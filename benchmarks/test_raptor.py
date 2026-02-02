"""RAPTOR retrieval tests."""

import pytest

from src.rag.raptor import build_raptor_tree, retrieve_multilevel


def test_build_raptor_tree():
    chunks = [
        {"text": "First chunk. Second sentence.", "index": 0},
        {"text": "Another chunk. More content.", "index": 1},
    ]
    nodes = build_raptor_tree(chunks, max_levels=2)
    assert len(nodes) >= 2
    assert any(n.get("level") == 0 for n in nodes)


def test_retrieve_multilevel():
    chunks = [{"text": "Python is a language.", "index": 0}]
    tree = build_raptor_tree(chunks)
    result = retrieve_multilevel("Python language", tree, top_k=2)
    assert len(result) >= 1
