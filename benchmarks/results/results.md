# Benchmark results

Embedder: `hashing-char2-5+word1-2-2048` · Python 3.13.18 · 2026-11-08

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
| vector | 0.93 | 1.00 | 1.00 | 0.97 | 0.97 | — |
| keyword | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | — |
| graph | 0.52 | 0.52 | 0.52 | 0.52 | 0.52 | en-1, en-4, en-6, en-9, ar-1, ar-1b, ar-3, ar-5, ar-5b, ar-7, ar-9, ar-10, ar-11, mix-1 |
| hybrid | 0.97 | 1.00 | 1.00 | 0.98 | 0.99 | — |

Hybrid Hit@3 by query language: ar 1.00 (n=15), en 1.00 (n=13), mixed 1.00 (n=1)

**Corpus: pdf**

| Retriever | Hit@1 | Hit@3 | Hit@5 | MRR@5 | nDCG@5 | Misses |
|---|---|---|---|---|---|---|
| vector | 0.90 | 1.00 | 1.00 | 0.95 | 0.96 | — |
| keyword | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | — |
| graph | 0.52 | 0.52 | 0.52 | 0.52 | 0.52 | en-1, en-4, en-6, en-9, ar-1, ar-1b, ar-3, ar-5, ar-5b, ar-7, ar-9, ar-10, ar-11, mix-1 |
| hybrid | 0.97 | 1.00 | 1.00 | 0.98 | 0.99 | — |

Hybrid Hit@3 by query language: ar 1.00 (n=15), en 1.00 (n=13), mixed 1.00 (n=1)

## 3. Chunking quality

| Group | Section-crossing rate ↓ | Clean boundary rate ↑ | Intra-chunk coherence ↑ | Coherence gap ↑ | Size CV |
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

| File | Tokens | Chunks | Load s | Chunk s | Embed s | RAPTOR s | Store s | Total s | Tokens/s | Peak MB |
|---|---|---|---|---|---|---|---|---|---|---|
| coffee_history.docx | 654 | 6 | 0.0516 | 0.0009 | 0.0325 | 0.0441 | 0.0821 | 0.2298 | 2846 | 2.22 |
| coffee_history.pdf | 654 | 6 | 0.1013 | 0.0009 | 0.0384 | 0.0323 | 0.0562 | 0.2471 | 2647 | 1.21 |
| water_ar.txt | 342 | 5 | 0.0004 | 0.0006 | 0.0274 | 0.0196 | 0.0629 | 0.1384 | 2471 | 0.7 |
| water_ar.docx | 342 | 5 | 0.0622 | 0.0006 | 0.0275 | 0.0258 | 0.0811 | 0.2206 | 1550 | 2.22 |
| water_ar.pdf | 342 | 5 | 0.7093 | 0.0006 | 0.0308 | 0.0197 | 0.0633 | 0.8483 | 403 | 2.77 |
| inspection_report.txt | 292 | 3 | 0.0004 | 0.0006 | 0.0173 | 0.0075 | 0.0267 | 0.0557 | 5242 | 0.45 |
| inspection_report.pdf | 292 | 3 | 0.0694 | 0.0008 | 0.0205 | 0.0092 | 0.0309 | 0.1341 | 2177 | 0.65 |
| employee_form_ar.docx | 170 | 2 | 0.1358 | 0.0005 | 0.016 | 0.0125 | 0.0297 | 0.2 | 850 | 2.22 |
| employee_form_ar.doc | 170 | 2 | 0.2339 | 0.0005 | 0.0204 | 0.0121 | 0.0283 | 0.3007 | 565 | 0.38 |

Query latency: vector p50 2.64 ms / p95 3.22 ms, keyword p50 0.14 ms / p95 0.28 ms, graph p50 0.12 ms / p95 0.24 ms, hybrid p50 3.3 ms / p95 3.66 ms


| Documents | Leaf chunks | Ingest s | Docs/s | Hybrid query p50 ms |
|---|---|---|---|---|
| 5 | 31 | 0.13 | 39.5 | 3.33 |
| 20 | 120 | 0.54 | 37.1 | 3.73 |
| 50 | 300 | 1.31 | 38.0 | 6.76 |
| 100 | 600 | 2.85 | 35.0 | 8.17 |

## 5. Arabic-specific tests

- **Diacritics preserved end-to-end:** ✅ — source 1298 marks, SQL 1298, vector store 1298 (DOCX: 1298)
- **Diacritic-insensitive retrieval:** ✅ — vocalized vs bare query pairs with identical top-1: 3/3, word-level agreement 100%
- **Normalization cases:** ✅ 10/10 (hamza forms, taa marbuta, alef maqsura, tatweel, harakat, Arabic-Indic digits, PDF presentation forms)
- **Legacy encodings:** ✅ utf-8→utf-8, utf-16→utf-16, cp1256→cp1256
- **Language / direction detection:** ✅
- **Arabic PDF fidelity:** bare-text similarity 100.0%, garble score 0.0, diacritics recovered 89% (extractor per page: pypdf, pypdf)
