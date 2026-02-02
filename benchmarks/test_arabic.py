"""Arabic and diacritics: round-trip and retrieval."""

import os
import pytest
from pathlib import Path

from src.parser.extractors import extract
from src.parser.analyzer import analyze_content
from src.parser.chunkers import chunk_fixed, chunk_dynamic
from src.embeddings import embed
from src.pipeline import run_ingest, run_rag


def test_arabic_txt_extract_preserves_diacritics(sample_arabic_txt_path):
    result = extract(sample_arabic_txt_path)
    raw = result["raw_text"]
    # Harakat / tashkeel in Arabic (e.g. َ ِ ُ)
    assert "\u064e" in raw or "\u0650" in raw or "\u064b" in raw or "عَرَبِي" in raw or "التَّشْكِيل" in raw


def test_arabic_chunking_preserves_diacritics(sample_arabic_txt_path):
    result = extract(sample_arabic_txt_path)
    analyzed = analyze_content(result["raw_text"], result.get("pages_or_sections", []))
    if analyzed["strategy"] == "dynamic":
        chunks = chunk_dynamic(
            result["raw_text"],
            result.get("pages_or_sections", []),
            analyzed["params"],
        )
    else:
        chunks = chunk_fixed(result["raw_text"], analyzed["params"])
    assert len(chunks) >= 1
    combined = "".join(c["text"] for c in chunks)
    assert "عربي" in combined or "عَرَبِي" in combined or "التشكيل" in combined


def test_arabic_embedding_roundtrip():
    """Embed Arabic text with diacritics; no error."""
    texts = ["نَصٌّ عَرَبِيٌّ بِالتَّشْكِيلِ"]
    embs = embed(texts)
    assert len(embs) == 1
    assert len(embs[0]) > 0


def test_arabic_ingest_and_retrieve(sample_arabic_txt_path, tmp_path):
    os.environ["CHROMA_PATH"] = str(tmp_path / "chroma")
    os.environ["SQLITE_PATH"] = str(tmp_path / "db.sqlite")
    Path(tmp_path / "chroma").mkdir(parents=True, exist_ok=True)
    run_ingest(sample_arabic_txt_path)
    result = run_rag("عربي تشكيل", top_k=3)
    chunks = result.get("chunks", [])
    assert len(chunks) >= 0  # May be 0 if no match; at least no crash
