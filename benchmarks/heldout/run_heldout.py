"""Held-out evaluation: documents and questions the parser was not developed on.

    python -m benchmarks.heldout.build_heldout   # once, builds the documents
    python -m benchmarks.heldout.run_heldout

Reports strategy accuracy, retrieval Hit@1/Hit@3/MRR by query kind
(lexical / paraphrase / cross-language) and the behaviour on broken files.
Writes benchmarks/heldout/results.md.
"""
from __future__ import annotations

import json
import sys
import statistics
import time
from collections import defaultdict
from pathlib import Path

from pyxon_parser import PyxonParser
from pyxon_parser.analyzer import analyze
from pyxon_parser.arabic import normalize_for_index
from pyxon_parser.embeddings import get_embedder
from pyxon_parser.loaders import load_document

HERE = Path(__file__).parent
DOCS = HERE / "docs"


def main() -> None:
    # Windows consoles default to cp1252 when output is piped; Arabic would crash print()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    spec = json.loads((HERE / "queries.json").read_text(encoding="utf-8"))
    embedder = get_embedder()
    lines = [f"# Held-out evaluation\n\nEmbedder: `{embedder.name}` · {time.strftime('%Y-%m-%d')}\n",
             "Documents and questions written after the parser was built, in styles it was not tuned on "
             "(Arabic legal articles, Windows-1256 news, vocalized story, bilingual DOCX with a table, PDF manual, 41-chapter report).\n"]

    # 1. strategy
    lines.append("## 1. Strategy selection\n\n| File | Expected | Predicted | Headings | Chunks | Reason |\n|---|---|---|---|---|---|")
    ok = 0
    parser = PyxonParser(embedder=embedder, build_raptor=False)
    for name, expected in spec["expected_strategy"].items():
        _, a, _, chunks = parser.chunk_document(DOCS / name)
        ok += a.strategy == expected
        lines.append(f"| {name} | {expected} | {a.strategy} {'✅' if a.strategy == expected else '❌'} | "
                     f"{a.num_headings} | {len(chunks)} | {a.reasons[0]} |")
    lines.append(f"\n**Accuracy: {ok}/{len(spec['expected_strategy'])}**\n")
    print(f"strategy {ok}/{len(spec['expected_strategy'])}")

    # 2. retrieval
    by_kind, noise, misses = evaluate_retrieval(embedder, spec)
    lines.append("## 2. Retrieval (hybrid, k=5)\n\n| Query kind | n | Hit@1 | Hit@3 | Hit@5 | MRR |\n|---|---|---|---|---|---|")
    for kind in ["lexical", "paraphrase", "cross", "all"]:
        firsts = by_kind.get(kind, [])
        if not firsts:
            continue
        n = len(firsts)
        h = lambda k: sum(f is not None and f < k for f in firsts) / n  # noqa: E731
        mrr = statistics.fmean(0 if f is None else 1 / (f + 1) for f in firsts)
        lines.append(f"| {kind} | {n} | {h(1):.2f} | {h(3):.2f} | {h(5):.2f} | {mrr:.2f} |")
        print(f"{kind:10} n={n:2} hit@1={h(1):.2f} hit@3={h(3):.2f} mrr={mrr:.2f}")
    lines.append(f"\nNoise: {noise:.0%} of returned results come from a different document than the answer.")
    print(f"noise      {noise:.0%} of returned results are from another document")
    if misses:
        lines.append("\nQueries not answered at rank 1:\n\n| id | kind | query | result | top file |\n|---|---|---|---|---|")
        lines.extend(misses)

    # 3. broken inputs
    lines.append("\n## 3. Broken and unusual inputs\n\n| File | Outcome |\n|---|---|")
    for f in sorted(DOCS.glob("edge_*")):
        try:
            doc = load_document(f)
            a, _ = analyze(doc)
            outcome = f"parsed: {a.strategy}, {a.num_tokens} tokens"
        except Exception as exc:
            outcome = f"`{type(exc).__name__}`: {exc}"
        lines.append(f"| {f.name} | {outcome} |")

    (HERE / "results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[-12:]))


def evaluate_retrieval(embedder, spec: dict, k: int = 5):
    """Ingest the held-out corpus with ``embedder`` and score every query.
    Returns (first-hit rank per query kind, noise share, rows for queries missed at rank 1)."""
    parser = PyxonParser(embedder=embedder)
    for name in spec["corpus"]:
        parser.ingest(DOCS / name)
    by_kind: dict[str, list] = defaultdict(list)
    wrong_file: list[float] = []  # share of returned results that come from another document (noise)
    misses = []
    for q in spec["queries"]:
        res = parser.search(q["query"], k=k)
        ev = normalize_for_index(q["evidence"])
        ranks = [i for i, r in enumerate(res) if r.filename == q["file"] and ev in normalize_for_index(r.text)]
        if res:
            wrong_file.append(sum(r.filename != q["file"] for r in res) / len(res))
        first = ranks[0] if ranks else None
        by_kind[q["kind"]].append(first)
        by_kind["all"].append(first)
        if first is None or first > 0:
            top = res[0].filename if res else "—"
            misses.append(f"| {q['id']} | {q['kind']} | {q['query']} | {'not in top 5' if first is None else f'rank {first + 1}'} | {top} |")
    parser.close()
    return by_kind, (statistics.fmean(wrong_file) if wrong_file else 0.0), misses


def hit_at(firsts: list, k: int) -> float:
    return sum(f is not None and f < k for f in firsts) / len(firsts) if firsts else 0.0


if __name__ == "__main__":
    main()
