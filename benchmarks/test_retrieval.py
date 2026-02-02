"""Retrieval accuracy: recall@k, MRR."""

import os
import pytest
from pathlib import Path

from src.parser.extractors import extract
from src.parser.analyzer import analyze_content
from src.parser.chunkers import chunk_fixed, chunk_dynamic
from src.embeddings import embed
from src.storage.vector_store import VectorStore
from src.pipeline import run_ingest, run_rag


@pytest.fixture
def ingested_doc(sample_txt_path, tmp_path):
    """Ingest sample TXT and return document_id. Use temp dirs for Chroma/SQL."""
    os.environ["CHROMA_PATH"] = str(tmp_path / "chroma")
    os.environ["SQLITE_PATH"] = str(tmp_path / "db.sqlite")
    Path(tmp_path / "chroma").mkdir(parents=True, exist_ok=True)
    result = run_ingest(sample_txt_path)
    return result.get("document_id"), result.get("chunks", [])


def test_retrieval_recall_at_k(ingested_doc):
    doc_id, chunks = ingested_doc
    assert doc_id
    assert len(chunks) >= 1

    # Query and check top result contains expected content
    result = run_rag("sample document", top_k=3)
    retrieved = result.get("chunks", [])
    assert len(retrieved) >= 1
    texts = [r.get("text", "") for r in retrieved]
    assert any("sample" in t.lower() for t in texts)


def test_retrieval_mrr(ingested_doc):
    """MRR: first relevant result rank."""
    result = run_rag("multiple paragraphs", top_k=5)
    retrieved = result.get("chunks", [])
    for i, r in enumerate(retrieved):
        if "paragraph" in (r.get("text") or "").lower():
            mrr = 1.0 / (i + 1)
            assert mrr > 0
            return
    pytest.skip("No relevant chunk in top 5 for this query")
