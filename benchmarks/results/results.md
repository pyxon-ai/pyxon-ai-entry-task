# Benchmark results

Embedder: `hashing-char2-5+word1-2-2048` · Python 3.13.18 · 2026-11-09

## 1. Strategy selection — accuracy 100%

| File | Expected | Predicted | Score | Detected type |
|---|---|---|---|---|
| coffee_history.docx | dynamic | dynamic ✅ | 0.9 | book / multi-section document |
| coffee_history.pdf | dynamic | dynamic ✅ | 0.9 | book / multi-section document |
| water_ar.txt | dynamic | dynamic ✅ | 0.9 | book / multi-section document |
| water_ar.docx | dynamic | dynamic ✅ | 0.9 | book / multi-section document |
| water_ar.pdf | dynamic | dynamic ✅ | 0.9 | book / multi-section document |
| inspection_report.txt | fixed | fixed ✅ | -1.8 | form / structured report |
| inspection_report.pdf | fixed | fixed ✅ | -1.2 | form / structured report |
| employee_form_ar.docx | fixed | fixed ✅ | -1.2 | form / structured report |
| employee_form_ar.doc | fixed | fixed ✅ | -1.2 | form / structured report |

## 2. Retrieval accuracy

**Corpus: editable (txt/docx/doc)**

| Retriever | Hit@1 | Hit@3 | Hit@5 | MRR@5 | nDCG@5 | Misses |
|---|---|---|---|---|---|---|
| vector | 0.93 | 1.00 | 1.00 | 0.97 | 0.96 | — |
| keyword | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | — |
| graph | 0.52 | 0.52 | 0.52 | 0.52 | 0.52 | en-1, en-4, en-6, en-9, ar-1, ar-1b, ar-3, ar-5, ar-5b, ar-7, ar-9, ar-10, ar-11, mix-1 |
| hybrid | 0.97 | 1.00 | 1.00 | 0.98 | 0.99 | — |

Hybrid Hit@3 by query language: ar 1.00 (n=15), en 1.00 (n=13), mixed 1.00 (n=1)

**Corpus: pdf**

| Retriever | Hit@1 | Hit@3 | Hit@5 | MRR@5 | nDCG@5 | Misses |
|---|---|---|---|---|---|---|
| vector | 0.90 | 1.00 | 1.00 | 0.95 | 0.95 | — |
| keyword | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | — |
| graph | 0.52 | 0.52 | 0.52 | 0.52 | 0.52 | en-1, en-4, en-6, en-9, ar-1, ar-1b, ar-3, ar-5, ar-5b, ar-7, ar-9, ar-10, ar-11, mix-1 |
| hybrid | 0.97 | 1.00 | 1.00 | 0.98 | 0.99 | — |

Hybrid Hit@3 by query language: ar 1.00 (n=15), en 1.00 (n=13), mixed 1.00 (n=1)

## 3. Chunking quality

| Group | Section-crossing rate ↓ | Ends on a complete source sentence ↑ | Intra-chunk coherence ↑ | Coherence gap ↑ | Size CV |
|---|---|---|---|---|---|
| fixed (all docs) | 0.409 | 1.000 | 0.292 | -0.031 | 0.260 |
| dynamic (all docs) | 0.000 | 1.000 | 0.333 | 0.140 | 0.107 |
| auto-selected | 0.000 | 1.000 | 0.302 | -0.002 | 0.189 |

<details><summary>Per document</summary>

| File | Strategy | Auto? | Chunks | Avg tokens | Crossing | Coherence | Gap |
|---|---|---|---|---|---|---|---|
| coffee_history.docx | fixed |  | 7 | 97.1 | 0.714 | 0.299 | -0.023 |
| coffee_history.docx | dynamic | ✓ | 6 | 102.2 | 0.0 | 0.308 | 0.012 |
| coffee_history.pdf | fixed |  | 7 | 97.1 | 0.714 | 0.299 | -0.023 |
| coffee_history.pdf | dynamic | ✓ | 6 | 102.2 | 0.0 | 0.308 | 0.012 |
| water_ar.txt | fixed |  | 4 | 89.8 | 0.75 | 0.224 | -0.037 |
| water_ar.txt | dynamic | ✓ | 5 | 62.6 | 0.0 | 0.249 | 0.026 |
| water_ar.docx | fixed |  | 4 | 89.0 | 0.75 | 0.222 | -0.037 |
| water_ar.docx | dynamic | ✓ | 5 | 62.0 | 0.0 | 0.245 | 0.023 |
| water_ar.pdf | fixed |  | 4 | 89.8 | 0.75 | 0.224 | -0.037 |
| water_ar.pdf | dynamic | ✓ | 5 | 62.6 | 0.0 | 0.249 | 0.026 |
| inspection_report.txt | fixed | ✓ | 3 | 98.7 | 0.0 | 0.214 | -0.018 |
| inspection_report.txt | dynamic |  | 2 | 143.0 | 0.0 | 0.233 | -0.006 |
| inspection_report.pdf | fixed | ✓ | 3 | 109.7 | 0.0 | 0.232 | -0.014 |
| inspection_report.pdf | dynamic |  | 6 | 48.7 | 0.0 | 0.217 | -0.023 |
| employee_form_ar.docx | fixed | ✓ | 2 | 91.5 | 0.0 | 0.458 | -0.044 |
| employee_form_ar.docx | dynamic |  | 1 | 164.0 | 0.0 | 0.594 | 0.594 |
| employee_form_ar.doc | fixed | ✓ | 2 | 91.5 | 0.0 | 0.458 | -0.044 |
| employee_form_ar.doc | dynamic |  | 1 | 164.0 | 0.0 | 0.594 | 0.594 |

</details>

## 4. Performance

| File | Tokens | Chunks | Load s | Chunk s | Embed s | RAPTOR s | Store s | Total s | Tokens/s | Python peak MB | Process RSS MB |
|---|---|---|---|---|---|---|---|---|---|---|---|
| coffee_history.docx | 654 | 6 | 0.0726 | 0.0024 | 0.0466 | 0.0415 | 0.0778 | 0.2682 | 2438 | 2.22 | 311.0 |
| coffee_history.pdf | 654 | 6 | 0.0977 | 0.0016 | 0.0375 | 0.031 | 0.0553 | 0.242 | 2702 | 1.21 | 311.1 |
| water_ar.txt | 342 | 5 | 0.0006 | 0.0011 | 0.0278 | 0.0215 | 0.0546 | 0.1347 | 2539 | 0.71 | 311.2 |
| water_ar.docx | 342 | 5 | 0.0567 | 0.001 | 0.0273 | 0.0226 | 0.0589 | 0.1955 | 1749 | 2.22 | 311.2 |
| water_ar.pdf | 342 | 5 | 0.6652 | 0.0011 | 0.0341 | 0.0291 | 0.0698 | 0.8321 | 411 | 2.77 | 311.3 |
| inspection_report.txt | 292 | 3 | 0.0007 | 0.0008 | 0.0247 | 0.008 | 0.0278 | 0.0661 | 4418 | 0.45 | 311.3 |
| inspection_report.pdf | 292 | 3 | 0.0675 | 0.0008 | 0.0203 | 0.0095 | 0.0284 | 0.13 | 2246 | 0.65 | 311.3 |
| employee_form_ar.docx | 170 | 2 | 0.1372 | 0.0005 | 0.0176 | 0.0149 | 0.0349 | 0.2128 | 799 | 2.22 | 311.3 |
| employee_form_ar.doc | 170 | 2 | 0.2453 | 0.0007 | 0.0251 | 0.0175 | 0.0313 | 0.33 | 515 | 0.39 | 311.4 |

Query latency: vector p50 18.34 ms / p95 51.74 ms, keyword p50 0.37 ms / p95 19.61 ms, graph p50 0.18 ms / p95 1.55 ms, hybrid p50 3.56 ms / p95 22.29 ms


| Documents | Leaf chunks | Ingest s | Docs/s | Hybrid query p50 ms |
|---|---|---|---|---|
| 5 | 28 | 0.12 | 42.4 | 19.09 |
| 20 | 110 | 0.58 | 34.4 | 8.89 |
| 50 | 275 | 1.49 | 33.5 | 6.24 |
| 100 | 550 | 2.61 | 38.3 | 10.36 |

## 5. Arabic-specific tests

- **Diacritics preserved end-to-end:** ✅ — source 1298 marks, SQL 1298, vector store 1298 (DOCX: 1298)
- **Diacritic-insensitive retrieval:** ✅ — vocalized vs bare query pairs with identical top-1: 3/3, word-level agreement 100%
- **Normalization cases:** ✅ 10/10 (hamza forms, taa marbuta, alef maqsura, tatweel, harakat, Arabic-Indic digits, PDF presentation forms)
- **Legacy encodings:** ✅ utf-8→utf-8, utf-16→utf-16, cp1256→cp1256, iso-8859-6→iso-8859-6
- **Language / direction detection:** ✅
- **Arabic PDF fidelity:** bare-text similarity 100.0%, garble score 0.0, diacritics recovered 89% (extractor per page: pypdf, pypdf)
- **Scanned Arabic PDF (OCR, Tesseract ara+eng):** character similarity 99.9%, word recall 98.4%, 1.0 s/page
