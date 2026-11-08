"""Pyxon parser benchmark suite.

    python -m benchmarks.run_benchmark            # full run, writes benchmarks/results/
    python -m benchmarks.run_benchmark --quick    # skip the larger scalability sizes

Sections
--------
1. Strategy selection  - does the analyzer pick the expected chunking strategy?
2. Retrieval accuracy  - Hit@1/3/5, MRR@5, nDCG@5 per retriever (vector / keyword / graph / hybrid),
                         on the editable-format corpus (TXT/DOCX/DOC) and the PDF corpus.
3. Chunking quality    - size stats, sentence-boundary integrity, section-boundary violations,
                         semantic coherence (intra-chunk similarity) and separation (vs neighbours),
                         fixed vs dynamic on every document.
4. Performance         - ingest latency per stage, throughput, peak Python memory, query latency
                         p50/p95, and scalability as the corpus grows.
5. Arabic-specific     - diacritics preserved end-to-end, diacritic-insensitive retrieval,
                         normalization cases, legacy encodings, RTL detection, PDF extraction fidelity.
"""
from __future__ import annotations

import argparse
import difflib
import json
import sys
import math
import platform
import statistics
import tempfile
import time
import tracemalloc
from pathlib import Path

import numpy as np
import psutil

from pyxon_parser import PyxonParser
from pyxon_parser.analyzer import analyze
from pyxon_parser.arabic import (
    DIACRITICS_RE, detect_language, diacritic_stats, normalize_for_index, strip_diacritics, text_direction,
)
from pyxon_parser.chunking import DynamicChunker, FixedChunker
from pyxon_parser.embeddings import get_embedder
from pyxon_parser.loaders import arabic_garble_score, decode_text, find_soffice, load_document
from pyxon_parser.text import split_sentences

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "samples"
OUT = Path(__file__).resolve().parent / "results"

EXPECTED_STRATEGY = {
    "coffee_history.docx": "dynamic", "coffee_history.pdf": "dynamic",
    "water_ar.txt": "dynamic", "water_ar.docx": "dynamic", "water_ar.pdf": "dynamic",
    "inspection_report.txt": "fixed", "inspection_report.pdf": "fixed",
    "employee_form_ar.docx": "fixed", "employee_form_ar.doc": "fixed",
}
CORPORA = {
    "editable (txt/docx/doc)": ["coffee_history.docx", "inspection_report.txt", "water_ar.txt", "employee_form_ar.doc"],
    "pdf": ["coffee_history.pdf", "inspection_report.pdf", "water_ar.pdf", "employee_form_ar.docx"],
}
MODES = ["vector", "keyword", "graph", "hybrid"]

# Legacy .doc needs LibreOffice; without it, skip .doc files and use the .docx copy in the corpus.
if find_soffice() is None:
    print("LibreOffice not found: skipping .doc samples (using .docx instead)")
    EXPECTED_STRATEGY = {k: v for k, v in EXPECTED_STRATEGY.items() if not k.endswith(".doc")}
    CORPORA = {c: [f[:-4] + ".docx" if f.endswith(".doc") else f for f in files] for c, files in CORPORA.items()}


def family(filename: str) -> str:
    return Path(filename).stem


def is_relevant(result, q) -> bool:
    return family(result.filename) == q["family"] and normalize_for_index(q["evidence"]) in normalize_for_index(result.text)


def count_relevant(parser, q) -> int:
    """Number of leaf chunks in the index that are relevant to q (ground truth for ideal DCG)."""
    ev = normalize_for_index(q["evidence"])
    rows = parser.sql.conn.execute(
        "SELECT d.filename, c.normalized_text FROM chunks c JOIN documents d ON d.id = c.document_id WHERE c.level = 0"
    ).fetchall()
    return sum(family(r["filename"]) == q["family"] and ev in r["normalized_text"] for r in rows)


# ---------------------------------------------------------------------------
def bench_strategy(embedder) -> dict:
    parser = PyxonParser(embedder=embedder, build_raptor=False)
    rows = []
    for name, expected in EXPECTED_STRATEGY.items():
        _, analysis, _, _ = parser.chunk_document(SAMPLES / name)
        rows.append({"file": name, "expected": expected, "predicted": analysis.strategy,
                     "score": analysis.strategy_score, "doc_type": analysis.doc_type,
                     "correct": analysis.strategy == expected})
    return {"accuracy": sum(r["correct"] for r in rows) / len(rows), "rows": rows}


def bench_retrieval(embedder, queries) -> dict:
    out = {}
    for corpus, files in CORPORA.items():
        parser = PyxonParser(embedder=embedder)
        for f in files:
            parser.ingest(SAMPLES / f)
        total_relevant = {q["id"]: count_relevant(parser, q) for q in queries}
        per_mode = {}
        for mode in MODES:
            hits1 = hits3 = hits5 = 0
            rr, ndcg, failures = [], [], []
            for q in queries:
                res = parser.search(q["query"], k=5, mode=mode)
                rel = [is_relevant(r, q) for r in res]
                first = next((i for i, r in enumerate(rel) if r), None)
                hits1 += first == 0
                hits3 += first is not None and first < 3
                hits5 += first is not None
                rr.append(0 if first is None else 1 / (first + 1))
                dcg = sum(1 / math.log2(i + 2) for i, r in enumerate(rel) if r)
                # ideal DCG from the ground truth: every relevant chunk in the index, not only
                # the ones this ranking happened to retrieve
                n_rel = total_relevant[q["id"]]
                idcg = sum(1 / math.log2(i + 2) for i in range(min(n_rel, 5)))
                ndcg.append(dcg / idcg if idcg else 0)
                if first is None:
                    failures.append(q["id"])
            n = len(queries)
            per_mode[mode] = {"hit@1": round(hits1 / n, 3), "hit@3": round(hits3 / n, 3),
                              "hit@5": round(hits5 / n, 3), "mrr@5": round(statistics.fmean(rr), 3),
                              "ndcg@5": round(statistics.fmean(ndcg), 3), "misses": failures}
        # per-language breakdown for hybrid
        by_lang = {}
        for lang in sorted({q["lang"] for q in queries}):
            qs = [q for q in queries if q["lang"] == lang]
            ok = 0
            for q in qs:
                res = parser.search(q["query"], k=3, mode="hybrid")
                ok += any(is_relevant(r, q) for r in res)
            by_lang[lang] = {"n": len(qs), "hit@3": round(ok / len(qs), 3)}
        out[corpus] = {"modes": per_mode, "hybrid_by_language": by_lang}
    return out


def _chunk_quality(chunks, sections, embedder) -> dict:
    sizes = [c.token_count for c in chunks]
    sent_section = {}
    source_sentences = []
    for s in sections:
        for b in s.blocks:
            for sent in split_sentences(b.text):
                sent_section.setdefault(sent.strip(), s.title)
                source_sentences.append(" ".join(sent.split()))
    crossings, clean_end, intra, inter = 0, 0, [], []
    sent_vecs = [embedder.embed(split_sentences(c.text) or [c.text]) for c in chunks]
    for i, c in enumerate(chunks):
        sents = split_sentences(c.text)
        secs = {sent_section.get(s.strip()) for s in sents} - {None}
        crossings += len(secs) > 1
        # clean = the chunk ends exactly where a complete source sentence ends (a forced cut
        # inside a sentence, even a punctuation-less one, does not count)
        text = " ".join(c.text.split())
        clean_end += any(text.endswith(src) for src in source_sentences if src)
        v = sent_vecs[i]
        if len(v) >= 2:
            sim = v @ v.T
            intra.append(float((sim.sum() - np.trace(sim)) / (len(v) * (len(v) - 1))))
        if i:  # sentence-level similarity across the boundary with the previous chunk
            inter.append(float((v @ sent_vecs[i - 1].T).mean()))
    coherence = statistics.fmean(intra) if intra else 0.0
    separation = statistics.fmean(inter) if inter else 0.0
    return {
        "chunks": len(chunks),
        "avg_tokens": round(statistics.fmean(sizes), 1),
        "size_cv": round(statistics.pstdev(sizes) / statistics.fmean(sizes), 3) if len(sizes) > 1 else 0.0,
        "min_tokens": min(sizes), "max_tokens": max(sizes),
        "section_crossing_rate": round(crossings / len(chunks), 3),
        "clean_boundary_rate": round(clean_end / len(chunks), 3),
        "intra_chunk_coherence": round(coherence, 3),
        "cross_boundary_similarity": round(separation, 3),
        "coherence_gap": round(coherence - separation, 3),
    }


def bench_chunking(embedder) -> dict:
    fixed, dynamic = FixedChunker(120, 20), DynamicChunker(embedder, 40, 220)
    rows = []
    for name in EXPECTED_STRATEGY:
        parsed = load_document(SAMPLES / name)
        analysis, sections = analyze(parsed)
        for label, chunker in (("fixed", fixed), ("dynamic", dynamic)):
            chunks = chunker.chunk(sections)
            rows.append({"file": name, "strategy": label, "auto_choice": analysis.strategy == label,
                         **_chunk_quality(chunks, sections, embedder)})

    def agg(rs):
        keys = ["section_crossing_rate", "clean_boundary_rate", "intra_chunk_coherence", "coherence_gap", "size_cv"]
        return {k: round(statistics.fmean(r[k] for r in rs), 3) for k in keys}

    return {
        "rows": rows,
        "summary": {
            "fixed (all docs)": agg([r for r in rows if r["strategy"] == "fixed"]),
            "dynamic (all docs)": agg([r for r in rows if r["strategy"] == "dynamic"]),
            "auto-selected": agg([r for r in rows if r["auto_choice"]]),
        },
    }


def _synthetic_doc(i: int, tmp: Path) -> Path:
    """Generate distinct documents for the scalability test (mix of Arabic and English)."""
    src = (SAMPLES / ("water_ar.txt" if i % 2 else "coffee_history.docx"))
    if src.suffix == ".txt":
        text = src.read_text(encoding="utf-8")
    else:
        text = load_document(src).text
    text = f"Synthetic copy {i}. رقم النسخة {i}.\n\n" + text.replace("الْمَاءُ", f"الْمَاءُ {i}")
    p = tmp / f"synthetic_{i}.txt"
    p.write_text(text, encoding="utf-8")
    return p


def bench_performance(embedder, queries, quick: bool) -> dict:
    # per-document ingest timings + memory
    parser = PyxonParser(embedder=embedder)
    ingest = []
    for name in EXPECTED_STRATEGY:
        tracemalloc.start()
        r = parser.ingest(SAMPLES / name)
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        rss = psutil.Process().memory_info().rss  # whole process: Python + native libs + vector index
        tokens = r.analysis.num_tokens
        ingest.append({"file": name, "tokens": tokens, "chunks": len(r.chunks), **r.timings,
                       "tokens_per_sec": round(tokens / r.timings["total"]) if r.timings["total"] else None,
                       "peak_mem_mb": round(peak / 2**20, 2), "rss_mb": round(rss / 2**20, 1)})

    latency = {}
    for mode in MODES:
        ts = []
        for q in queries:
            t0 = time.perf_counter()
            parser.search(q["query"], k=5, mode=mode)
            ts.append((time.perf_counter() - t0) * 1000)
        latency[mode] = {"p50_ms": round(statistics.median(ts), 2),
                         "p95_ms": round(float(np.percentile(ts, 95)), 2)}

    # scalability
    sizes = [5, 20] if quick else [5, 20, 50, 100]
    scale = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        docs = [_synthetic_doc(i, tmp) for i in range(max(sizes))]
        for n in sizes:
            p = PyxonParser(embedder=embedder, build_raptor=True)
            t0 = time.perf_counter()
            for d in docs[:n]:
                p.ingest(d)
            ingest_s = time.perf_counter() - t0
            ts = []
            for q in queries[:15]:
                t1 = time.perf_counter()
                p.search(q["query"], k=5)
                ts.append((time.perf_counter() - t1) * 1000)
            stats = p.sql.stats()
            scale.append({"documents": n, "leaf_chunks": stats["leaf_chunks"], "ingest_s": round(ingest_s, 2),
                          "docs_per_sec": round(n / ingest_s, 1), "hybrid_p50_ms": round(statistics.median(ts), 2)})
    return {"ingest": ingest, "query_latency": latency, "scalability": scale}


def bench_arabic(embedder, queries) -> dict:
    results = {}

    # 1. diacritics preserved through load -> chunk -> SQL -> vector store
    src = (SAMPLES / "water_ar.txt").read_text(encoding="utf-8")
    parser = PyxonParser(embedder=embedder)
    r = parser.ingest(SAMPLES / "water_ar.txt", strategy="dynamic")
    stored = parser.sql.document_chunks(r.document_id, level=0)
    titles = [r["title"] for r in parser.sql.conn.execute("SELECT title FROM sections WHERE document_id = ?", (r.document_id,))]
    stored_text = " ".join(c["text"] for c in stored) + " " + " ".join(titles)  # chunks + section headings
    vec_docs = parser.vectors.collection.get(where={"$and": [{"document_id": r.document_id}, {"level": 0}]})["documents"]
    src_stats, sql_stats = diacritic_stats(src), diacritic_stats(stored_text)
    results["diacritics_preserved"] = {
        "source_total": src_stats["total"], "sql_total": sql_stats["total"],
        "vector_store_total": len(DIACRITICS_RE.findall(" ".join(vec_docs + titles))),
        "per_mark_equal": all(src_stats[k] == sql_stats[k] for k in src_stats),
        "passed": src_stats == sql_stats and len(DIACRITICS_RE.findall(" ".join(vec_docs + titles))) == src_stats["total"],
    }
    for f in ["water_ar.docx"]:
        r2 = parser.ingest(SAMPLES / f, strategy="dynamic")
        t = " ".join(c["text"] for c in parser.sql.document_chunks(r2.document_id, level=0)) + " " + " ".join(
            row["title"] for row in parser.sql.conn.execute("SELECT title FROM sections WHERE document_id = ?", (r2.document_id,)))
        results["diacritics_preserved"][f"{f}_total"] = diacritic_stats(t)["total"]

    # 2. diacritic-insensitive retrieval: vocalized and bare variants must agree
    variants = [q for q in queries if q.get("variant_of")]
    by_id = {q["id"]: q for q in queries}
    agree = []
    for v in variants:
        base = by_id[v["variant_of"]]
        top_a = parser.search(base["query"], k=1)[0].chunk_id
        top_b = parser.search(v["query"], k=1)[0].chunk_id
        agree.append({"pair": [base["query"], v["query"]], "same_top1": top_a == top_b})
    # fully strip / fully keep on a set of single words
    words = ["الْهَيْدرُوجِينِ", "النَّوَاعِيرَ", "مَأْرِبَ", "الْجَفَافِ"]
    word_hits = []
    for w in words:
        a = parser.search(w, k=1, mode="keyword")
        b = parser.search(strip_diacritics(w), k=1, mode="keyword")
        word_hits.append(bool(a and b and a[0].chunk_id == b[0].chunk_id))
    results["diacritic_insensitive_retrieval"] = {
        "query_pairs": agree,
        "word_level_agreement": round(sum(word_hits) / len(word_hits), 3),
        "passed": all(x["same_top1"] for x in agree) and all(word_hits),
    }

    # 3. normalization cases
    cases = [
        ("أحمد", "احمد"), ("إسلام", "اسلام"), ("آمال", "امال"), ("مدرسة", "مدرسه"), ("مستشفى", "مستشفي"),
        ("مسؤول", "مسوول"), ("العـــربية", "العربيه"), ("كِتَابٌ", "كتاب"), ("١٢٣٤", "1234"),
        ("ﻫﻠﻠ", "هلل"),  # presentation forms from PDFs
    ]
    norm = [{"input": a, "expected": b, "got": normalize_for_index(a), "ok": normalize_for_index(a) == b} for a, b in cases]
    results["normalization"] = {"cases": norm, "passed": all(c["ok"] for c in norm)}

    # 4. encodings
    sample = "الْمَاءُ أَصْلُ الْحَيَاةِ"
    enc = {}
    for e in ["utf-8", "utf-16", "cp1256", "iso-8859-6"]:
        raw = sample.encode(e)  # all four can represent vocalized Arabic
        text, detected = decode_text(raw)
        enc[e] = {"detected": detected, "roundtrip": text == sample}
    results["encodings"] = {"cases": enc, "passed": all(v["roundtrip"] for v in enc.values())}

    # 5. language + direction detection
    checks = [("الْمَاءُ أَصْلُ الْحَيَاةِ", "ar", "rtl"), ("Coffee began in Ethiopia", "en", "ltr"),
              ("Machine learning تعلم الآلة", "mixed", "ltr")]
    lang = [{"text": t, "lang": detect_language(t), "dir": text_direction(t), "ok": detect_language(t) == l and text_direction(t) == d}
            for t, l, d in checks]
    results["language_direction"] = {"cases": lang, "passed": all(x["ok"] for x in lang)}

    # 6. PDF extraction fidelity vs. the source text
    pdf_text = load_document(SAMPLES / "water_ar.pdf").text
    a = normalize_for_index(src).replace(" ", "")
    b = normalize_for_index(pdf_text).replace(" ", "")
    results["pdf_fidelity"] = {
        "char_similarity_bare": round(difflib.SequenceMatcher(None, a, b, autojunk=False).ratio(), 3),
        "garble_score": round(arabic_garble_score(pdf_text), 3),
        "diacritics_recovered_ratio": round(diacritic_stats(pdf_text)["total"] / src_stats["total"], 3),
        "extractor_per_page": load_document(SAMPLES / "water_ar.pdf").meta["extractor_per_page"],
    }
    return results


# ---------------------------------------------------------------------------
def to_markdown(res: dict) -> str:
    L = [f"# Benchmark results\n\nEmbedder: `{res['embedder']}` · Python {res['python']} · {res['date']}\n"]
    s = res["strategy"]
    L.append(f"## 1. Strategy selection — accuracy {s['accuracy']:.0%}\n\n| File | Expected | Predicted | Score | Detected type |\n|---|---|---|---|---|")
    for r in s["rows"]:
        L.append(f"| {r['file']} | {r['expected']} | {r['predicted']} {'✅' if r['correct'] else '❌'} | {r['score']} | {r['doc_type']} |")
    L.append("\n## 2. Retrieval accuracy\n")
    for corpus, data in res["retrieval"].items():
        L.append(f"**Corpus: {corpus}**\n\n| Retriever | Hit@1 | Hit@3 | Hit@5 | MRR@5 | nDCG@5 | Misses |\n|---|---|---|---|---|---|---|")
        for m, v in data["modes"].items():
            L.append(f"| {m} | {v['hit@1']:.2f} | {v['hit@3']:.2f} | {v['hit@5']:.2f} | {v['mrr@5']:.2f} | {v['ndcg@5']:.2f} | {', '.join(v['misses']) or '—'} |")
        L.append("\nHybrid Hit@3 by query language: " + ", ".join(f"{k} {v['hit@3']:.2f} (n={v['n']})" for k, v in data["hybrid_by_language"].items()) + "\n")
    L.append("## 3. Chunking quality\n\n| Group | Section-crossing rate ↓ | Ends on a complete source sentence ↑ | Intra-chunk coherence ↑ | Coherence gap ↑ | Size CV |\n|---|---|---|---|---|---|")
    for k, v in res["chunking"]["summary"].items():
        L.append(f"| {k} | {v['section_crossing_rate']:.3f} | {v['clean_boundary_rate']:.3f} | {v['intra_chunk_coherence']:.3f} | {v['coherence_gap']:.3f} | {v['size_cv']:.3f} |")
    L.append("\n<details><summary>Per document</summary>\n\n| File | Strategy | Auto? | Chunks | Avg tokens | Crossing | Coherence | Gap |\n|---|---|---|---|---|---|---|---|")
    for r in res["chunking"]["rows"]:
        L.append(f"| {r['file']} | {r['strategy']} | {'✓' if r['auto_choice'] else ''} | {r['chunks']} | {r['avg_tokens']} | {r['section_crossing_rate']} | {r['intra_chunk_coherence']} | {r['coherence_gap']} |")
    L.append("\n</details>\n\n## 4. Performance\n\n| File | Tokens | Chunks | Load s | Chunk s | Embed s | RAPTOR s | Store s | Total s | Tokens/s | Python peak MB | Process RSS MB |\n|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in res["performance"]["ingest"]:
        L.append(f"| {r['file']} | {r['tokens']} | {r['chunks']} | {r['load']} | {r['chunk']} | {r['embed']} | {r['raptor']} | {r['store']} | {r['total']} | {r['tokens_per_sec']} | {r['peak_mem_mb']} | {r['rss_mb']} |")
    L.append("\nQuery latency: " + ", ".join(f"{m} p50 {v['p50_ms']} ms / p95 {v['p95_ms']} ms" for m, v in res["performance"]["query_latency"].items()))
    L.append("\n\n| Documents | Leaf chunks | Ingest s | Docs/s | Hybrid query p50 ms |\n|---|---|---|---|---|")
    for r in res["performance"]["scalability"]:
        L.append(f"| {r['documents']} | {r['leaf_chunks']} | {r['ingest_s']} | {r['docs_per_sec']} | {r['hybrid_p50_ms']} |")
    a = res["arabic"]
    d = a["diacritics_preserved"]
    L.append("\n## 5. Arabic-specific tests\n")
    L.append(f"- **Diacritics preserved end-to-end:** {'✅' if d['passed'] else '❌'} — source {d['source_total']} marks, SQL {d['sql_total']}, vector store {d['vector_store_total']} (DOCX: {d.get('water_ar.docx_total')})")
    di = a["diacritic_insensitive_retrieval"]
    L.append(f"- **Diacritic-insensitive retrieval:** {'✅' if di['passed'] else '❌'} — vocalized vs bare query pairs with identical top-1: {sum(x['same_top1'] for x in di['query_pairs'])}/{len(di['query_pairs'])}, word-level agreement {di['word_level_agreement']:.0%}")
    L.append(f"- **Normalization cases:** {'✅' if a['normalization']['passed'] else '❌'} {sum(c['ok'] for c in a['normalization']['cases'])}/{len(a['normalization']['cases'])} (hamza forms, taa marbuta, alef maqsura, tatweel, harakat, Arabic-Indic digits, PDF presentation forms)")
    L.append(f"- **Legacy encodings:** {'✅' if a['encodings']['passed'] else '❌'} " + ", ".join(f"{k}→{v['detected']}" for k, v in a['encodings']['cases'].items()))
    L.append(f"- **Language / direction detection:** {'✅' if a['language_direction']['passed'] else '❌'}")
    p = a["pdf_fidelity"]
    L.append(f"- **Arabic PDF fidelity:** bare-text similarity {p['char_similarity_bare']:.1%}, garble score {p['garble_score']}, diacritics recovered {p['diacritics_recovered_ratio']:.0%} (extractor per page: {', '.join(p['extractor_per_page'])})\n")
    return "\n".join(L)


def main() -> None:
    # Windows consoles default to cp1252 when output is piped; Arabic would crash print()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--embedder", default=None, help="'hashing' or a sentence-transformers model name")
    args = ap.parse_args()

    embedder = get_embedder(args.embedder)
    queries = json.loads((Path(__file__).parent / "queries.json").read_text(encoding="utf-8"))["queries"]
    res = {"embedder": embedder.name, "python": platform.python_version(), "date": time.strftime("%Y-%m-%d")}
    for name, fn in [
        ("strategy", lambda: bench_strategy(embedder)),
        ("retrieval", lambda: bench_retrieval(embedder, queries)),
        ("chunking", lambda: bench_chunking(embedder)),
        ("performance", lambda: bench_performance(embedder, queries, args.quick)),
        ("arabic", lambda: bench_arabic(embedder, queries)),
    ]:
        t0 = time.perf_counter()
        res[name] = fn()
        print(f"[{name}] done in {time.perf_counter() - t0:.1f}s")

    OUT.mkdir(exist_ok=True)
    (OUT / "results.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    md = to_markdown(res)
    (OUT / "results.md").write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
