# Pyxon AI — Arabic-aware Document Parser for RAG

My solution to the [Pyxon AI junior engineer entry task](TASK.md): a document parser that reads **PDF, DOCX, DOC and TXT**, works out the document's structure, **chooses fixed or dynamic chunking on its own**, and stores the results in a **vector DB (Chroma)** and a **SQL DB (SQLite)**. It also adds a knowledge graph, a RAPTOR summary tree, hybrid retrieval and a RAG layer. Arabic is fully supported, including **harakat/tashkeel**. Diacritics are kept exactly as written in storage, and matching ignores them.

```
             ┌──────────────┐   ┌────────────────┐   ┌──────────────────────┐
 PDF/DOCX ──▶│   loaders    │──▶│    analyzer    │──▶│  Fixed  | Dynamic    │
 DOC/TXT     │ PyMuPDF+pypdf│   │ structure,lang,│   │ chunker | chunker    │
             │ python-docx  │   │ harakat, score │   │ (window)| (sections +│
             │ LibreOffice  │   │ → strategy     │   │         |  semantic) │
             └──────────────┘   └────────────────┘   └─────────┬────────────┘
                                                               ▼
           ┌──────────────────────────── embed (multilingual) ────────────────┐
           ▼                         ▼                          ▼             ▼
   Chroma (vectors)        SQLite: documents,         Knowledge graph   RAPTOR tree
   leaf + summary nodes    sections, chunks, FTS5     (terms, edges,    (k-means →
                           BM25, terms, edges         PageRank)         summaries)
           └───────────────┬─────────┴──────────────────────┘
                           ▼
          Hybrid retriever (vector + BM25 + graph, RRF fusion)
                           ▼
          RAG: SQL router for structured questions · grounded LLM prompt · extractive fallback
```

## Features

| Requirement | How it is done |
|---|---|
| PDF | **PyMuPDF** for layout blocks and font sizes, so headings are detected from font size. **pypdf** is a second extractor. For each page, the loader keeps whichever output is *less garbled* (`arabic_garble_score`), because some Arabic PDFs only extract in logical order with one of the two. Arabic presentation forms (U+FB50–U+FEFF) are NFKC-normalized back to base letters. |
| DOCX | python-docx with **heading styles** (Heading 1–n / Title) as structure, plus tables flattened row by row |
| DOC | Converted headlessly with LibreOffice (`soffice --convert-to docx`), then parsed as DOCX |
| TXT | Encoding detection: UTF-8 (with or without BOM), UTF-16, **Windows-1256**, ISO-8859-6 |
| Content understanding | `analyzer.py` detects headings (styles, font size, markdown, `Chapter/Section`, `الفصل/الباب/القسم`, numbering, short-title heuristics), paragraph and section length variance, `key: value` form fields, language, text direction, diacritic density, TF-IDF keywords and an extractive summary |
| Strategy choice | A transparent weighted score (headings +, uneven sections +, varied paragraphs +, form fields −, very short −). The UI and DB store the *reasons* (e.g. "5 headings detected → structure-aware splitting keeps sections intact") |
| Fixed chunking | ~120-word windows that only cut at sentence boundaries, with ~20 words of sentence overlap |
| Dynamic chunking | Sections first, so a chunk never spans two chapters. Long sections are split where meaning shifts (similarity between neighbouring sentence windows drops below a percentile of the section). Tiny fragments are merged into a neighbour |
| Vector DB | **Chroma** (persistent, cosine HNSW) with chunk metadata (doc id, level, section, strategy, language) |
| SQL DB | **SQLite**: `documents`, `sections`, `chunks`, `chunks_fts` (FTS5/BM25), `terms`, `term_edges` |
| Arabic | Original text is always stored. A normalized form (no harakat or tatweel; unified أ/إ/آ/ٱ→ا, ى→ي, ة→ه, ؤ/ئ; Arabic-Indic digits; light ال-stemming) is used for embeddings, BM25 and the graph. RTL text is rendered with `dir="auto"` in the demo |
| Graph RAG | Concept co-occurrence graph per document (TF-IDF key terms per chunk, PageRank centrality). The retriever expands query terms one hop |
| RAPTOR | Leaf embeddings are clustered with k-means, each cluster is summarized (LLM if configured, extractive otherwise), and the process repeats up to a root. Summary nodes are stored as `level ≥ 1` for "collapsed tree" retrieval |
| Hybrid retrieval | Vector + BM25 + graph rankings fused with weighted **Reciprocal Rank Fusion**. Every hit shows which retrievers found it and at what rank |
| RAG integration | `RAGPipeline.ask()` sends structured questions ("how many documents…", "كم عدد الملفات") to **read-only SQL**. Everything else goes through retrieval, a cited prompt and an LLM (Anthropic or any OpenAI-compatible API via env vars), with an extractive answer as fallback when no key is set |

## Quick start

```bash
pip install -r requirements.txt          # Python 3.10+
python app.py                            # demo on http://localhost:7860 (sample docs auto-load)
pytest -q                                # 36 tests
python -m benchmarks.run_benchmark       # writes benchmarks/results/results.{md,json}
```

Python API:

```python
from pyxon_parser import PyxonParser

parser = PyxonParser(data_dir="data")                 # SQLite + Chroma under ./data
res = parser.ingest("samples/water_ar.pdf")           # strategy="auto" | "fixed" | "dynamic"
print(res.analysis.strategy, res.analysis.reasons)

for hit in parser.search("سد مأرب", k=3):             # with or without harakat
    print(hit.filename, hit.section, hit.sources, hit.text[:80])

print(parser.ask("ما هي علامات الجفاف؟").answer)
print(parser.ask("How many documents are indexed?").rows)   # routed to SQL
```

Configuration (environment variables):

| Variable | Default | Meaning |
|---|---|---|
| `PYXON_EMBEDDER` | `auto` | `auto` uses `intfloat/multilingual-e5-small` when `sentence-transformers` is installed and the model can be downloaded, and falls back to `hashing` otherwise. You can also pass any sentence-transformers model name |
| `PYXON_DATA_DIR` | `./data` | Where the demo keeps SQLite and Chroma |
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` | none | Turns on LLM answers. `PYXON_LLM_MODEL` and `OPENAI_BASE_URL` are optional |

## Live demo

**🔗 https://pyxon-document-parser-1n4n.onrender.com** (free tier: the first load after a quiet period takes about a minute while the server wakes up)

The Gradio app (`app.py`) has six tabs: parse (upload, analysis, chunks, RAPTOR tree), search (pick a retriever), ask (RAG), SQL explorer, library and benchmark results. The sample corpus loads at startup, and the Arabic files with harakat are one click away.

**Deploying (free) on Render:** New → Web Service → connect this repository → Language **Docker** → Instance type **Free**. The included `Dockerfile` installs LibreOffice (for `.doc` files) and starts the app on the port Render provides. On the free tier the service sleeps after 15 minutes without traffic, so the first request after that takes about a minute while it wakes up. The same `Dockerfile` works on Railway, Fly.io, Google Cloud Run or a Docker Space on Hugging Face.

## Benchmarks

`benchmarks/run_benchmark.py` runs five sections. Full output is in [`benchmarks/results/results.md`](benchmarks/results/results.md). The headline numbers below come from the **offline hashing embedder** on a 2-vCPU container:

* **Strategy selection:** 9/9 files get the expected strategy (8/8 when LibreOffice is not installed and the `.doc` sample is skipped). This holds across formats: the same content as DOCX, PDF and TXT gets the same decision.
* **Retrieval** (29 queries: 13 English, 15 Arabic, 1 mixed, including vocalized and bare variants of the same question):

  | Corpus | Retriever | Hit@1 | Hit@3 | MRR@5 | nDCG@5 |
  |---|---|---|---|---|---|
  | TXT/DOCX/DOC | vector | 0.90 | 1.00 | 0.95 | 0.96 |
  | | keyword (BM25) | 1.00 | 1.00 | 1.00 | 1.00 |
  | | graph alone | 0.48 | 0.48 | 0.48 | 0.48 |
  | | **hybrid** | **0.97** | **1.00** | **0.98** | **0.99** |
  | PDF | **hybrid** | **0.97** | **1.00** | **0.98** | **0.99** |
* **Chunking quality:** dynamic chunking has a **0%** section-crossing rate, against 41% for fixed windows on the same documents. 100% of chunks end on a sentence boundary. The auto-selected strategy has the best intra-chunk coherence.
* **Performance:** 0.05–0.3 s to ingest each sample (0.76 s for the Arabic PDF, which runs two extractors). Peak memory is under 3 MB per document. Hybrid query p50 is about 3 ms. At **100 documents / 600 chunks**, ingest runs at about 40 docs/s and hybrid query p50 is about 10 ms.
* **Arabic:** all 1,298 harakat survive end to end (source = SQL = Chroma, for both TXT and DOCX). Vocalized and bare queries return the same top-1 (3/3 pairs, 4/4 single words). Normalization passes 10/10 cases, cp1256 and UTF-16 decode correctly, and the Arabic PDF's bare text matches the source 100%.

How to read these numbers: the corpus is small (4 documents per corpus, by design so that relevance can be labelled exactly), so retrieval scores are near their ceiling. The hashing embedder is lexical, which is why BM25 is so strong on its own. The benchmark is built so that switching to a neural embedder (`--embedder intfloat/multilingual-e5-small`) or adding harder query sets needs no code changes.

## Project layout

```
pyxon_parser/
  arabic.py      harakat handling, normalization, language/direction detection
  loaders.py     PDF (PyMuPDF + pypdf), DOCX, DOC (LibreOffice), TXT (encoding detection)
  analyzer.py    structure + content analysis, strategy scoring
  chunking.py    FixedChunker, DynamicChunker
  embeddings.py  multilingual sentence-transformers or hashing fallback
  storage.py     SQLStore (SQLite + FTS5), VectorStore (Chroma)
  graph.py       concept graph (Graph RAG)
  raptor.py      hierarchical summary tree
  retrieval.py   hybrid retriever with RRF
  rag.py         SQL routing, prompt building, LLM / extractive answers
  llm.py         Anthropic / OpenAI-compatible client (env-configured)
  pipeline.py    PyxonParser facade
app.py           Gradio demo
benchmarks/      queries.json, run_benchmark.py, results/
samples/         sample corpus (EN/AR, vocalized Arabic, forms) + build script
tests/           pytest suite
```

## Design decisions and trade-offs

* **Keep the original text, match on the normalized text.** Removing harakat at ingest would make search easy but would destroy information (حَمَلَ vs حُمِلَ). Storing both forms keeps fidelity and also gives diacritic-insensitive recall.
* **An explainable heuristic for strategy choice, not a black box.** The choice depends on a handful of interpretable signals, so a reviewer (or the UI) can see why. An LLM classifier could replace `analyze()` without changing anything else.
* **Hashing embedder fallback.** The demo must run anywhere, including without GPU or Hugging Face access. A character n-gram and word hashing vectorizer on normalized text is stateless (documents can be added incrementally), works for Arabic morphology, and costs under 3 ms per query. With network access the default switches to multilingual-e5.
* **SQLite FTS5 for BM25** instead of a separate keyword index: one less service, and it stays in the same database as the metadata.
* **RRF fusion** instead of tuned score blending: robust to the very different score scales of cosine similarity and BM25.
* **Two PDF extractors** cost about 0.5 s per Arabic PDF, but they make Arabic PDFs readable when one extractor returns visual-order or broken text.

## Questions & assumptions

* *How is "intelligent" strategy selection judged?* → I assumed the decision must be automatic **and explainable**, and that a user can override it (`strategy=` / UI radio button).
* *Which embedding model?* → None was specified. I made the model pluggable, defaulted to multilingual-e5-small, and kept an offline fallback so the demo can't break.
* *Must an LLM be called?* → "Designed to integrate with a RAG system" suggested the LLM is pluggable. Answers use Anthropic or OpenAI when a key is present and extractive answers otherwise. No key is committed.
* *What counts as "structured queries"?* → Questions about the corpus itself (counts, languages, strategies, chunk stats) go to read-only SQL through intent rules. Arbitrary SELECTs can be run in the demo's SQL tab.
* *Scanned (image-only) PDFs?* → Assumed out of scope. OCR (e.g. Tesseract `ara`) would plug into `load_pdf`.

## Limitations and future work

* Shadda inside lam-alef ligatures can be lost in some PDFs (89% of harakat recovered from the sample PDF; the bare text is 100% correct). DOCX and TXT are lossless.
* The scanned-PDF/OCR path, table structure in PDFs and image captions are not implemented.
* Heading detection in plain TXT is heuristic. An LLM-based structure pass could be added for messy documents.
* With more data: tune the RRF weights and dynamic-chunk thresholds on a labelled set, add a cross-encoder re-ranker (e.g. multilingual BGE reranker) and an Arabic-specific embedder (e.g. a CAMeLBERT-based model).
