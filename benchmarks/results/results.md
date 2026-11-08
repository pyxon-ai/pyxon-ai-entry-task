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
| employee_form_ar.docx | fixed | fixed ✅ | -0.6 | form / structured report |
| employee_form_ar.doc | fixed | fixed ✅ | -0.6 | form / structured report |

## 2. Retrieval accuracy

**Corpus: editable (txt/docx/doc)**

| Retriever | Hit@1 | Hit@3 | Hit@5 | MRR@5 | nDCG@5 | Misses |
|---|---|---|---|---|---|---|
| vector | 0.90 | 1.00 | 1.00 | 0.95 | 0.96 | — |
| keyword | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | — |
| graph | 0.48 | 0.48 | 0.48 | 0.48 | 0.48 | en-1, en-4, en-6, en-9, ar-1, ar-1b, ar-3, ar-5, ar-5b, ar-7, ar-9, ar-10, ar-11, ar-12, mix-1 |
| hybrid | 0.97 | 1.00 | 1.00 | 0.98 | 0.99 | — |

Hybrid Hit@3 by query language: ar 1.00 (n=15), en 1.00 (n=13), mixed 1.00 (n=1)

**Corpus: pdf**

| Retriever | Hit@1 | Hit@3 | Hit@5 | MRR@5 | nDCG@5 | Misses |
|---|---|---|---|---|---|---|
| vector | 0.86 | 1.00 | 1.00 | 0.93 | 0.94 | — |
| keyword | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | — |
| graph | 0.48 | 0.48 | 0.48 | 0.48 | 0.48 | en-1, en-4, en-6, en-9, ar-1, ar-1b, ar-3, ar-5, ar-5b, ar-7, ar-9, ar-10, ar-11, ar-12, mix-1 |
| hybrid | 0.97 | 1.00 | 1.00 | 0.98 | 0.99 | — |

Hybrid Hit@3 by query language: ar 1.00 (n=15), en 1.00 (n=13), mixed 1.00 (n=1)

## 3. Chunking quality

| Group | Section-crossing rate ↓ | Clean boundary rate ↑ | Intra-chunk coherence ↑ | Coherence gap ↑ | Size CV |
|---|---|---|---|---|---|
| fixed (all docs) | 0.409 | 1.000 | 0.315 | -0.030 | 0.276 |
| dynamic (all docs) | 0.000 | 1.000 | 0.260 | -0.021 | 0.189 |
| auto-selected | 0.000 | 1.000 | 0.326 | -0.001 | 0.205 |

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
| inspection_report.txt | fixed | ✓ | 3 | 98.7 | 0.0 | 0.193 | -0.019 |
| inspection_report.txt | dynamic |  | 3 | 95.3 | 0.0 | 0.204 | -0.007 |
| inspection_report.pdf | fixed | ✓ | 3 | 109.7 | 0.0 | 0.204 | -0.019 |
| inspection_report.pdf | dynamic |  | 5 | 58.4 | 0.0 | 0.179 | -0.021 |
| employee_form_ar.docx | fixed | ✓ | 2 | 83.0 | 0.0 | 0.587 | -0.036 |
| employee_form_ar.docx | dynamic |  | 6 | 24.8 | 0.0 | 0.297 | -0.132 |
| employee_form_ar.doc | fixed | ✓ | 2 | 83.0 | 0.0 | 0.587 | -0.036 |
| employee_form_ar.doc | dynamic |  | 6 | 24.8 | 0.0 | 0.297 | -0.132 |

</details>

## 4. Performance

| File | Tokens | Chunks | Load s | Chunk s | Embed s | RAPTOR s | Store s | Total s | Tokens/s | Peak MB |
|---|---|---|---|---|---|---|---|---|---|---|
| coffee_history.docx | 654 | 6 | 0.05 | 0.0009 | 0.0323 | 0.0278 | 0.0589 | 0.188 | 3479 | 2.22 |
| coffee_history.pdf | 654 | 6 | 0.0965 | 0.0009 | 0.0367 | 0.0299 | 0.0546 | 0.2363 | 2768 | 1.21 |
| water_ar.txt | 342 | 5 | 0.0003 | 0.0005 | 0.0247 | 0.0165 | 0.0484 | 0.1136 | 3011 | 0.7 |
| water_ar.docx | 342 | 5 | 0.0551 | 0.0005 | 0.0247 | 0.0162 | 0.0485 | 0.1696 | 2017 | 2.22 |
| water_ar.pdf | 342 | 5 | 0.6144 | 0.0006 | 0.03 | 0.0191 | 0.0577 | 0.7471 | 458 | 2.77 |
| inspection_report.txt | 292 | 3 | 0.0003 | 0.0006 | 0.0163 | 0.0055 | 0.0244 | 0.0521 | 5605 | 0.45 |
| inspection_report.pdf | 292 | 3 | 0.0676 | 0.0007 | 0.0208 | 0.0064 | 0.0287 | 0.1295 | 2255 | 0.65 |
| employee_form_ar.docx | 170 | 2 | 0.1457 | 0.0004 | 0.0138 | 0.013 | 0.028 | 0.2136 | 796 | 2.22 |
| employee_form_ar.doc | 170 | 2 | 0.2369 | 0.0004 | 0.0139 | 0.0138 | 0.0284 | 0.3042 | 559 | 0.37 |

Query latency: vector p50 2.63 ms / p95 3.15 ms, keyword p50 0.15 ms / p95 0.24 ms, graph p50 0.12 ms / p95 0.26 ms, hybrid p50 3.02 ms / p95 3.47 ms


| Documents | Leaf chunks | Ingest s | Docs/s | Hybrid query p50 ms |
|---|---|---|---|---|
| 5 | 31 | 0.12 | 43.3 | 2.82 |
| 20 | 120 | 0.52 | 38.3 | 3.7 |
| 50 | 300 | 1.2 | 41.6 | 4.98 |
| 100 | 600 | 2.48 | 40.3 | 10.52 |

## 5. Arabic-specific tests

- **Diacritics preserved end-to-end:** ✅ — source 1298 marks, SQL 1298, vector store 1298 (DOCX: 1298)
- **Diacritic-insensitive retrieval:** ✅ — vocalized vs bare query pairs with identical top-1: 3/3, word-level agreement 100%
- **Normalization cases:** ✅ 10/10 (hamza forms, taa marbuta, alef maqsura, tatweel, harakat, Arabic-Indic digits, PDF presentation forms)
- **Legacy encodings:** ✅ utf-8→utf-8, utf-16→utf-16, cp1256→cp1256
- **Language / direction detection:** ✅
- **Arabic PDF fidelity:** bare-text similarity 100.0%, garble score 0.0, diacritics recovered 89% (extractor per page: pypdf, pypdf)
