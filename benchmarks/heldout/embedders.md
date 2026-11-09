# Embedding models on the evaluation set

28 questions (15 on Arabic documents), hybrid retrieval, k=5. `arabert` = Omartificial-Intelligence-Space/GATE-AraBert-v1, `camelbert` = CAMeL-Lab/bert-base-arabic-camelbert-msa.

| Embedder | Exact wording Hit@3 | Paraphrase Hit@3 | English q → Arabic doc | Arabic docs Hit@3 | All Hit@1 | All Hit@3 | MRR | Noise | Load + run |
|---|---|---|---|---|---|---|---|---|---|
| `hashing` (hashing-char2-5+word1-2-2048, 2048-d) | 1.00 | 0.29 | miss | 0.73 | 0.75 | 0.79 | 0.77 | 28% | 1 s + 6 s |

* `arabert`: could not be loaded here (see the log above); skipped.
