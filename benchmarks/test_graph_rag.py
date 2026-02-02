"""Graph RAG retrieval tests."""

import pytest

from src.rag.graph_rag import build_graph, retrieve_subgraph


def test_build_graph():
    chunks = [
        {"text": "Alice met Bob. Bob works at Acme.", "index": 0},
        {"text": "Bob and Charlie are friends.", "index": 1},
    ]
    G = build_graph(chunks)
    assert G.number_of_nodes() >= 1
    assert G.number_of_edges() >= 0


def test_retrieve_subgraph_without_graph():
    chunks = [{"text": "Hello world.", "index": 0}]
    result = retrieve_subgraph("world", chunks, graph=None, top_k=1)
    assert len(result) >= 1
    assert "Hello" in result[0].get("text", "") or "world" in result[0].get("text", "")
