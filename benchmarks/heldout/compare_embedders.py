"""Compare embedding models on the evaluation set (same documents, questions and hybrid retrieval).

    python -m benchmarks.heldout.compare_embedders                     # hashing, fastembed, arabert, camelbert
    python -m benchmarks.heldout.compare_embedders hashing arabert     # any PYXON_EMBEDDER values

Models that cannot be loaded (package not installed, no network) are reported and skipped.
Writes benchmarks/heldout/embedders.md.
"""
from __future__ import annotations

import json
import statistics
import sys
import time

from pyxon_parser.embeddings import ARABIC_MODELS, HashingEmbedder, get_embedder

from .run_heldout import HERE, evaluate_retrieval, hit_at

DEFAULT = ["hashing", "fastembed", "arabert", "camelbert"]


def main(choices: list[str]) -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    spec = json.loads((HERE / "queries.json").read_text(encoding="utf-8"))
    arabic_ids = {q["id"] for q in spec["queries"] if q["file"].startswith("ar_")}
    rows, notes = [], []
    for choice in choices:
        get_embedder.cache_clear()
        t0 = time.perf_counter()
        emb = get_embedder(choice)
        if choice != "hashing" and isinstance(emb, HashingEmbedder):
            notes.append(f"* `{choice}`: could not be loaded here (see the log above); skipped.")
            print(f"{choice}: not available, skipped")
            continue
        load_s = time.perf_counter() - t0
        t0 = time.perf_counter()
        by_kind, noise, _ = evaluate_retrieval(emb, spec)
        run_s = time.perf_counter() - t0
        firsts_ar = [f for q, f in zip(spec["queries"], by_kind["all"]) if q["id"] in arabic_ids]
        mrr = statistics.fmean(0 if f is None else 1 / (f + 1) for f in by_kind["all"])
        row = (f"| `{choice}` ({emb.name.split('/')[-1]}, {emb.dim}-d) | {hit_at(by_kind['lexical'], 3):.2f} | "
               f"{hit_at(by_kind['paraphrase'], 3):.2f} | {'rank ' + str(by_kind['cross'][0] + 1) if by_kind['cross'][0] is not None else 'miss'} | "
               f"{hit_at(firsts_ar, 3):.2f} | {hit_at(by_kind['all'], 1):.2f} | {hit_at(by_kind['all'], 3):.2f} | {mrr:.2f} | "
               f"{noise:.0%} | {load_s:.0f} s + {run_s:.0f} s |")
        rows.append(row)
        print(row)
    out = ["# Embedding models on the evaluation set\n",
           f"{len(spec['queries'])} questions ({len(arabic_ids)} on Arabic documents), hybrid retrieval, k=5. "
           "`arabert` = " + ARABIC_MODELS["arabert"] + ", `camelbert` = " + ARABIC_MODELS["camelbert"] + ".\n",
           "| Embedder | Exact wording Hit@3 | Paraphrase Hit@3 | English q → Arabic doc | Arabic docs Hit@3 | All Hit@1 | All Hit@3 | MRR | Noise | Load + run |",
           "|---|---|---|---|---|---|---|---|---|---|", *rows, "", *notes]
    (HERE / "embedders.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"\nwrote {HERE / 'embedders.md'}")


if __name__ == "__main__":
    main(sys.argv[1:] or DEFAULT)
