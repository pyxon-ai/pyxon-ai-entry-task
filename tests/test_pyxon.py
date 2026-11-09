"""Unit + integration tests.  Run:  pytest -q"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("PYXON_EMBEDDER", "hashing")  # fast, offline, deterministic

from pyxon_parser import PyxonParser  # noqa: E402
from pyxon_parser.analyzer import analyze  # noqa: E402
from pyxon_parser.arabic import (  # noqa: E402
    detect_language, diacritic_density, diacritic_stats, normalize_for_index, strip_diacritics, text_direction,
)
from pyxon_parser.chunking import DynamicChunker, FixedChunker  # noqa: E402
from pyxon_parser.embeddings import HashingEmbedder  # noqa: E402
from pyxon_parser.loaders import UnsupportedFileType, decode_text, find_soffice, load_document  # noqa: E402

SAMPLES = Path(__file__).resolve().parent.parent / "samples"
VOCALIZED = "الْمَاءُ هُوَ أَسَاسُ الْحَيَاةِ"


@pytest.fixture(scope="module")
def parser():
    p = PyxonParser()
    for f in ["coffee_history.docx", "inspection_report.txt", "water_ar.txt", "employee_form_ar.docx"]:
        p.ingest(SAMPLES / f)
    return p


# --- Arabic -----------------------------------------------------------------
def test_strip_diacritics_keeps_letters():
    assert strip_diacritics(VOCALIZED) == "الماء هو أساس الحياة"


def test_normalization_variants():
    assert normalize_for_index("أَحْمَد") == normalize_for_index("احمد")
    assert normalize_for_index("مدرسة") == normalize_for_index("مدرسه")
    assert normalize_for_index("العـــربية") == "العربيه"
    assert normalize_for_index("٢٠٢٥") == "2025"
    assert normalize_for_index("ﻫﻠﻠ") == "هلل"  # presentation forms


def test_language_direction_density():
    assert detect_language(VOCALIZED) == "ar" and text_direction(VOCALIZED) == "rtl"
    assert detect_language("hello world") == "en" and text_direction("hello") == "ltr"
    assert diacritic_density(VOCALIZED) > 0.5
    assert diacritic_density(strip_diacritics(VOCALIZED)) == 0


@pytest.mark.parametrize("enc", ["utf-8", "utf-16", "cp1256"])
def test_decode_encodings(enc):
    text = "مرحبا بالعالم"
    decoded, _ = decode_text(text.encode(enc))
    assert decoded == text


# --- loaders ----------------------------------------------------------------
NEEDS_LIBREOFFICE = pytest.mark.skipif(find_soffice() is None, reason="LibreOffice not installed (needed for .doc)")


@pytest.mark.parametrize("name", ["coffee_history.docx", "coffee_history.pdf", "water_ar.txt", "water_ar.docx",
                                  "water_ar.pdf", pytest.param("employee_form_ar.doc", marks=NEEDS_LIBREOFFICE),
                                  "inspection_report.pdf"])
def test_loaders_extract_text(name):
    doc = load_document(SAMPLES / name)
    assert len(doc.text) > 200
    assert doc.sha256


def test_unsupported_type(tmp_path):
    f = tmp_path / "x.xyz"
    f.write_text("hi")
    with pytest.raises(UnsupportedFileType):
        load_document(f)


def test_docx_keeps_diacritics():
    src = (SAMPLES / "water_ar.txt").read_text(encoding="utf-8")
    doc = load_document(SAMPLES / "water_ar.docx")
    assert diacritic_stats(doc.text) == diacritic_stats(src)


def test_arabic_pdf_is_readable():
    doc = load_document(SAMPLES / "water_ar.pdf")
    assert "سد مارب" in normalize_for_index(doc.text)


# --- analysis + chunking ----------------------------------------------------
@pytest.mark.parametrize("name,expected", [
    ("coffee_history.docx", "dynamic"), ("coffee_history.pdf", "dynamic"), ("water_ar.txt", "dynamic"),
    ("inspection_report.txt", "fixed"), ("employee_form_ar.docx", "fixed"),
])
def test_strategy_selection(name, expected):
    analysis, _ = analyze(load_document(SAMPLES / name))
    assert analysis.strategy == expected, analysis.reasons


def test_fixed_chunker_sizes_and_overlap():
    _, sections = analyze(load_document(SAMPLES / "inspection_report.txt"))
    chunks = FixedChunker(60, 15).chunk(sections)
    assert len(chunks) > 3
    assert all(c.token_count <= 75 for c in chunks)
    # the last (short) sentence of a chunk is carried into the next one as overlap
    from pyxon_parser.text import split_sentences

    carried = sum(split_sentences(chunks[i].text)[-1] in chunks[i + 1].text for i in range(len(chunks) - 1))
    assert carried >= (len(chunks) - 1) // 2


def test_dynamic_chunker_respects_sections():
    _, sections = analyze(load_document(SAMPLES / "coffee_history.docx"))
    chunks = DynamicChunker(HashingEmbedder(), 40, 220).chunk(sections)
    titles = {s.title for s in sections if s.title}
    assert {c.section for c in chunks} <= titles | {""}
    assert all(c.token_count <= 280 for c in chunks)


def test_dynamic_chunker_splits_long_sections():
    _, sections = analyze(load_document(SAMPLES / "coffee_history.docx"))
    chunks = DynamicChunker(HashingEmbedder(), 20, 60).chunk(sections)
    assert len(chunks) > len([s for s in sections if s.blocks])


# --- storage + retrieval + RAG ---------------------------------------------
def test_sql_and_vector_counts_match(parser):
    stats = parser.sql.stats()
    assert stats["documents"] == 4
    assert parser.vectors.count() == stats["leaf_chunks"] + stats["summary_nodes"]
    assert stats["summary_nodes"] > 0 and stats["terms"] > 0


def test_diacritics_stored(parser):
    doc_id = next(d["id"] for d in parser.sql.list_documents() if d["filename"] == "water_ar.txt")
    stored = " ".join(c["text"] for c in parser.sql.document_chunks(doc_id))
    assert diacritic_density(stored) > 0.5


@pytest.mark.parametrize("query,expected_file", [
    ("When did the governor of Mecca ban coffee?", "coffee_history.docx"),
    ("forklift hydraulic hose", "inspection_report.txt"),
    ("سد مأرب", "water_ar.txt"),
    ("سَدُّ مَأْرِبَ", "water_ar.txt"),
    ("مهندسة برمجيات", "employee_form_ar.docx"),
])
def test_hybrid_search(parser, query, expected_file):
    assert parser.search(query, k=3)[0].filename == expected_file


def test_diacritic_insensitive_top1(parser):
    a = parser.search("كَيْفَ تَتَكَوَّنُ السُّحُبُ؟", k=1)[0].chunk_id
    b = parser.search("كيف تتكون السحب", k=1)[0].chunk_id
    assert a == b


def test_rag_sql_route(parser):
    ans = parser.ask("How many documents are indexed?")
    assert ans.route == "sql" and ans.rows[0]["documents"] == 4


def test_rag_extractive_answer(parser):
    parser.rag.llm = None
    ans = parser.ask("Who invented the lever espresso machine?")
    assert ans.route == "rag" and "Gaggia" in ans.answer


def test_readonly_sql_guard(parser):
    with pytest.raises(ValueError):
        parser.sql.run_readonly_query("DELETE FROM documents")


def test_reingest_replaces(parser):
    before = parser.sql.stats()["documents"]
    parser.ingest(SAMPLES / "water_ar.txt")
    assert parser.sql.stats()["documents"] == before
