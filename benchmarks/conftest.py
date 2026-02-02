"""Pytest fixtures: sample doc paths, Arabic sample, gold query-chunk pairs."""

import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def sample_txt_path(tmp_path):
    """Sample TXT file. UTF-8, English."""
    p = tmp_path / "sample.txt"
    p.write_text(
        "This is a sample document for testing.\n\n"
        "It has multiple paragraphs. The parser should chunk it correctly.\n\n"
        "Section two contains more content for retrieval benchmarks.",
        encoding="utf-8",
    )
    return str(p)


@pytest.fixture
def sample_arabic_txt_path(tmp_path):
    """Sample TXT with Arabic and diacritics (harakat)."""
    # Arabic with diacritics example
    text = (
        "بسم الله الرحمن الرحيم.\n\n"
        "هَذَا نَصٌّ عَرَبِيٌّ بِالتَّشْكِيلِ. الْفِقْرَةُ الثَّانِيَةُ.\n\n"
        "نَختَبِرُ التَّرميزَ وَالاتِّجاهَ."
    )
    p = tmp_path / "sample_arabic.txt"
    p.write_text(text, encoding="utf-8")
    return str(p)


@pytest.fixture
def gold_query_chunk_pairs():
    """Gold query -> relevant chunk index (for retrieval accuracy). Pairs (query, expected_chunk_contains)."""
    return [
        ("sample document", "sample document"),
        ("multiple paragraphs", "multiple paragraphs"),
        ("Section two", "Section two"),
    ]


@pytest.fixture
def chroma_path(tmp_path):
    """Temporary Chroma path for tests."""
    d = tmp_path / "chroma_test"
    d.mkdir()
    return str(d)


@pytest.fixture
def sqlite_path(tmp_path):
    """Temporary SQLite path for tests."""
    return str(tmp_path / "test.db")
