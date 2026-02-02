"""Performance: ingest and retrieval latency."""

import os
import time
import pytest
from pathlib import Path

from src.pipeline import run_ingest, run_rag


@pytest.fixture
def small_doc_path(tmp_path):
    p = tmp_path / "small.txt"
    p.write_text("Short content. " * 50, encoding="utf-8")
    return str(p)


def test_ingest_latency(small_doc_path, tmp_path):
    os.environ["CHROMA_PATH"] = str(tmp_path / "chroma")
    os.environ["SQLITE_PATH"] = str(tmp_path / "perf.db")
    Path(tmp_path / "chroma").mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    run_ingest(small_doc_path)
    elapsed = time.perf_counter() - start
    assert elapsed < 60.0  # Ingest under 60s for small doc


def test_retrieval_latency(small_doc_path, tmp_path):
    os.environ["CHROMA_PATH"] = str(tmp_path / "chroma")
    os.environ["SQLITE_PATH"] = str(tmp_path / "perf.db")
    Path(tmp_path / "chroma").mkdir(parents=True, exist_ok=True)
    run_ingest(small_doc_path)
    start = time.perf_counter()
    run_rag("content", top_k=5)
    elapsed = time.perf_counter() - start
    assert elapsed < 30.0  # Retrieval under 30s
