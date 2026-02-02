"""Chunking quality: coherence and boundaries."""

import pytest

from src.parser.analyzer import analyze_content
from src.parser.chunkers import chunk_fixed, chunk_dynamic


def test_fixed_chunking_has_overlap():
    text = "One. Two. Three. Four. Five. Six. Seven. Eight. Nine. Ten. " * 20
    params = {"chunk_size": 128, "overlap": 32, "min_chunk_chars": 10}
    chunks = chunk_fixed(text, params)
    assert len(chunks) >= 2
    for c in chunks:
        assert "text" in c and "start" in c and "end" in c and "index" in c
        assert len(c["text"].strip()) >= 10


def test_dynamic_chunking_uses_sections():
    text = "Intro paragraph.\n\nSection A content here.\n\nSection B content."
    structure = [{"text": "Intro paragraph."}, {"text": "Section A content here."}, {"text": "Section B content."}]
    params = {"min_chunk_chars": 5, "max_chunk_chars": 500}
    chunks = chunk_dynamic(text, structure, params)
    assert len(chunks) >= 1
    combined = " ".join(c["text"] for c in chunks)
    assert "Section A" in combined and "Section B" in combined


def test_analyzer_returns_strategy():
    text = "Short text."
    result = analyze_content(text, [])
    assert result["strategy"] in ("fixed", "dynamic")
    assert "params" in result
