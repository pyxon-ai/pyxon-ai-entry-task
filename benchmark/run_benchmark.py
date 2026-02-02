import sys
import os
import json
import time

# -------------------------------------------------
# Add PROJECT ROOT to PYTHONPATH
# -------------------------------------------------
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)
sys.path.insert(0, PROJECT_ROOT)

from app.retrieval.retriever import Retriever
from benchmark.metrics import (
    precision_at_k,
    recall_at_k,
    chunk_quality,
    retrieval_accuracy
)

# -------------------------------------------------
# Benchmark Runner
# -------------------------------------------------
def run_benchmark(benchmark_file: str, k: int = 5):
    retriever = Retriever(top_k=k)

    with open(benchmark_file, "r", encoding="utf-8") as f:
        benchmark_data = json.load(f)

    precision_scores = []
    recall_scores = []
    latency_scores = []
    chunk_quality_scores = []
    keyword_accuracy_scores = []

    for item in benchmark_data:
        query = item["query"]
        expected_keywords = item.get("expected_keywords", [])
        relevant_chunk_ids = item.get("relevant_chunks", [])

        # -----------------------------
        # Retrieval + Latency
        # -----------------------------
        start = time.time()
        results = retriever.retrieve(query)
        latency = time.time() - start
        latency_scores.append(latency)

        # -----------------------------
        # DEBUG: show retrieved text
        # -----------------------------
        print("\n--- DEBUG: Retrieved Text (first 500 chars) ---")
        if results:
            print(results[0]["text"][:500])
        else:
            print("NO RESULTS RETURNED")
        print("---------------------------------------------\n")

        # -----------------------------
        # Keyword-based Retrieval Accuracy (MAIN METRIC)
        # -----------------------------
        all_text = " ".join([r["text"] for r in results]) if results else ""
        keyword_acc = retrieval_accuracy(all_text, expected_keywords)
        keyword_accuracy_scores.append(keyword_acc)

        # -----------------------------
        # Optional: Precision / Recall (secondary)
        # -----------------------------
        if relevant_chunk_ids:
            retrieved_ids = [r["chunk_id"] for r in results]
            p = precision_at_k(retrieved_ids, relevant_chunk_ids, k)
            r = recall_at_k(retrieved_ids, relevant_chunk_ids, k)
            precision_scores.append(p)
            recall_scores.append(r)
        else:
            p, r = None, None

        # -----------------------------
        # Chunk Quality (best chunk)
        # -----------------------------
        if results:
            best_text = results[0]["text"]
            chunk_quality_scores.append(chunk_quality(best_text))

        # -----------------------------
        # Per-query output
        # -----------------------------
        print(f"Query: {query}")
        print(f"Keyword Retrieval Accuracy: {keyword_acc:.2f}")

        if p is not None and r is not None:
            print(f"Precision@{k}: {p:.2f} | Recall@{k}: {r:.2f}")

        print(f"Latency: {latency:.3f}s")
        print("-" * 60)

    # -------------------------------------------------
    # Summary
    # -------------------------------------------------
    print("\n✅ Benchmark Results Summary")

    print(
        f"Avg Keyword Retrieval Accuracy: "
        f"{sum(keyword_accuracy_scores) / len(keyword_accuracy_scores):.2f}"
    )

    if precision_scores:
        print(f"Avg Precision@{k}: {sum(precision_scores)/len(precision_scores):.2f}")
        print(f"Avg Recall@{k}: {sum(recall_scores)/len(recall_scores):.2f}")

    if chunk_quality_scores:
        print(
            f"Avg Chunk Quality: "
            f"{sum(chunk_quality_scores)/len(chunk_quality_scores):.2f}"
        )

    print(f"Avg Latency: {sum(latency_scores)/len(latency_scores):.3f}s")


# -------------------------------------------------
# Entry Point
# -------------------------------------------------
if __name__ == "__main__":
    run_benchmark("benchmark/benchmark_data.json")