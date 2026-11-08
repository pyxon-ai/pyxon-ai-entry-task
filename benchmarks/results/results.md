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
| vector | 0.93 | 0.97 | 1.00 | 0.96 | 0.95 | — |
| keyword | 1.00 | 1.00 | 1.00 | 1.00 | 0.99 | — |
| graph | 0.52 | 0.52 | 0.52 | 0.52 | 0.52 | en-1, en-4, en-6, en-9, ar-1, ar-1b, ar-3, ar-5, ar-5b, ar-7, ar-9, ar-10, ar-11, mix-1 |
| hybrid | 0.97 | 1.00 | 1.00 | 0.98 | 0.97 | — |

Hybrid Hit@3 by query language: ar 1.00 (n=15), en 1.00 (n=13), mixed 1.00 (n=1)

**Corpus: pdf**

| Retriever | Hit@1 | Hit@3 | Hit@5 | MRR@5 | nDCG@5 | Misses |
|---|---|---|---|---|---|---|
| vector | 0.90 | 0.97 | 1.00 | 0.94 | 0.94 | — |
| keyword | 1.00 | 1.00 | 1.00 | 1.00 | 0.99 | — |
| graph | 0.52 | 0.52 | 0.52 | 0.52 | 0.52 | en-1, en-4, en-6, en-9, ar-1, ar-1b, ar-3, ar-5, ar-5b, ar-7, ar-9, ar-10, ar-11, mix-1 |
| hybrid | 0.97 | 1.00 | 1.00 | 0.98 | 0.97 | — |

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
| water_ar.txt | fixed |  | 4 | 89.8 | 0.75 | 0.223 | -0.036 |
| water_ar.txt | dynamic | ✓ | 5 | 62.6 | 0.0 | 0.248 | 0.027 |
| water_ar.docx | fixed |  | 4 | 89.0 | 0.75 | 0.221 | -0.037 |
| water_ar.docx | dynamic | ✓ | 5 | 62.0 | 0.0 | 0.245 | 0.024 |
| water_ar.pdf | fixed |  | 4 | 89.8 | 0.75 | 0.223 | -0.036 |
| water_ar.pdf | dynamic | ✓ | 5 | 62.6 | 0.0 | 0.248 | 0.027 |
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
| coffee_history.docx | 654 | 6 | 0.0559 | 0.0016 | 0.0336 | 0.0376 | 0.0618 | 0.2095 | 3122 | 2.22 | 310.8 |
| coffee_history.pdf | 654 | 6 | 0.1006 | 0.0016 | 0.0389 | 0.0316 | 0.0557 | 0.2475 | 2642 | 1.21 | 310.9 |
| water_ar.txt | 342 | 5 | 0.0005 | 0.0011 | 0.0256 | 0.0172 | 0.0494 | 0.1169 | 2926 | 0.7 | 310.9 |
| water_ar.docx | 342 | 5 | 0.0555 | 0.001 | 0.0249 | 0.017 | 0.0502 | 0.1715 | 1994 | 2.22 | 311.0 |
| water_ar.pdf | 342 | 5 | 0.6493 | 0.0011 | 0.0317 | 0.0207 | 0.0612 | 0.7894 | 433 | 2.77 | 311.0 |
| inspection_report.txt | 292 | 3 | 0.0005 | 0.0006 | 0.0173 | 0.0074 | 0.0274 | 0.0562 | 5196 | 0.45 | 311.1 |
| inspection_report.pdf | 292 | 3 | 0.0697 | 0.0008 | 0.0205 | 0.0095 | 0.028 | 0.1318 | 2215 | 0.65 | 311.1 |
| employee_form_ar.docx | 170 | 2 | 0.1352 | 0.0005 | 0.0156 | 0.0126 | 0.0285 | 0.1978 | 859 | 2.22 | 311.1 |
| employee_form_ar.doc | 170 | 2 | 0.2898 | 0.0007 | 0.0172 | 0.012 | 0.028 | 0.3563 | 477 | 0.38 | 311.1 |

Query latency: vector p50 27.52 ms / p95 61.19 ms, keyword p50 0.52 ms / p95 19.4 ms, graph p50 0.15 ms / p95 1.54 ms, hybrid p50 3.79 ms / p95 22.5 ms


| Documents | Leaf chunks | Ingest s | Docs/s | Hybrid query p50 ms |
|---|---|---|---|---|
| 5 | 28 | 0.14 | 35.3 | 20.23 |
| 20 | 110 | 0.53 | 37.6 | 5.54 |
| 50 | 275 | 1.28 | 39.1 | 7.25 |
| 100 | 550 | 2.76 | 36.3 | 10.3 |

## 5. Arabic-specific tests

- **Diacritics preserved end-to-end:** ✅ — source 1298 marks, SQL 1298, vector store 1298 (DOCX: 1298)
- **Diacritic-insensitive retrieval:** ✅ — vocalized vs bare query pairs with identical top-1: 3/3, word-level agreement 100%
- **Normalization cases:** ✅ 10/10 (hamza forms, taa marbuta, alef maqsura, tatweel, harakat, Arabic-Indic digits, PDF presentation forms)
- **Legacy encodings:** ✅ utf-8→utf-8, utf-16→utf-16, cp1256→cp1256, iso-8859-6→iso-8859-6
- **Language / direction detection:** ✅
- **Arabic PDF fidelity:** bare-text similarity 100.0%, garble score 0.0, diacritics recovered 89% (extractor per page: pypdf, pypdf)
