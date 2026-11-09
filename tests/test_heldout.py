"""Tests on the held-out corpus (documents the parser was not developed on) and on broken inputs.

Build the corpus first if it is missing:  python -m benchmarks.heldout.build_heldout
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("PYXON_EMBEDDER", "hashing")

from pyxon_parser import PyxonParser  # noqa: E402
from pyxon_parser.analyzer import analyze  # noqa: E402
from pyxon_parser.arabic import diacritic_stats, normalize_for_index  # noqa: E402
from pyxon_parser.loaders import (  # noqa: E402
    DocumentLoadError,
    EmptyDocumentError,
    UnsupportedFileType,
    load_document,
)

HELDOUT = Path(__file__).resolve().parent.parent / "benchmarks" / "heldout"
DOCS = HELDOUT / "docs"
SPEC = json.loads((HELDOUT / "queries.json").read_text(encoding="utf-8"))

pytestmark = pytest.mark.skipif(not DOCS.exists(), reason="held-out corpus not built")


@pytest.mark.parametrize("name,expected", list(SPEC["expected_strategy"].items()))
def test_heldout_strategy(name, expected):
    analysis, _ = analyze(load_document(DOCS / name))
    assert analysis.strategy == expected, analysis.reasons


def test_legal_articles_become_sections():
    _, sections = analyze(load_document(DOCS / "ar_law.txt"))
    titles = [s.title for s in sections if s.title]
    assert sum(t.startswith("المادة") for t in titles) == 7


def test_cp1256_news_is_decoded():
    doc = load_document(DOCS / "ar_news_cp1256.txt")
    assert doc.meta["encoding"] == "cp1256"
    assert "محطة جديدة لتحلية مياه البحر" in doc.text


def test_vocalized_story_keeps_every_haraka():
    src = (HELDOUT / "src" / "ar_story_vocalized.txt").read_text(encoding="utf-8")
    p = PyxonParser()
    r = p.ingest(DOCS / "ar_story_vocalized.txt")
    stored = " ".join(c["text"] for c in p.sql.document_chunks(r.document_id))
    titles = " ".join(row["title"] for row in p.sql.conn.execute(
        "SELECT title FROM sections WHERE document_id = ?", (r.document_id,)))
    assert diacritic_stats(stored + " " + titles) == diacritic_stats(src)


def test_bilingual_docx_table_is_searchable():
    doc = load_document(DOCS / "bilingual_policy.docx")
    assert "Leave type: Unpaid, Days per year: 30, Paid: No." in doc.text
    assert analyze(doc)[0].language == "mixed"


def test_pdf_and_markdown_versions_agree():
    a, _ = analyze(load_document(DOCS / "en_manual.md"))
    b, _ = analyze(load_document(DOCS / "en_manual.pdf"))
    assert (a.strategy, a.num_headings) == (b.strategy, b.num_headings)


@pytest.fixture(scope="module")
def corpus():
    p = PyxonParser()
    for name in SPEC["corpus"]:
        p.ingest(DOCS / name)
    return p


@pytest.mark.parametrize("q", [q for q in SPEC["queries"] if q["kind"] == "lexical"], ids=lambda q: q["id"])
def test_heldout_lexical_queries_in_top3(corpus, q):
    ev = normalize_for_index(q["evidence"])
    hits = corpus.search(q["query"], k=3)
    assert any(h.filename == q["file"] and ev in normalize_for_index(h.text) for h in hits)


# --- broken inputs: clear errors, never a crash or a silent empty index ------
@pytest.mark.parametrize("name,error", [
    ("edge_corrupt.pdf", DocumentLoadError),
    ("edge_fake.docx", DocumentLoadError),
    ("edge_empty.txt", EmptyDocumentError),
    ("edge_whitespace.txt", EmptyDocumentError),
    ("edge_image_only.pdf", EmptyDocumentError),
    ("edge_unknown.xyz", UnsupportedFileType),
])
def test_broken_inputs_raise_clear_errors(name, error):
    with pytest.raises(error):
        load_document(DOCS / name)


def test_image_only_pdf_mentions_ocr():
    with pytest.raises(EmptyDocumentError, match="OCR"):
        load_document(DOCS / "edge_image_only.pdf")


def test_failed_ingest_leaves_no_partial_document():
    p = PyxonParser()
    with pytest.raises(DocumentLoadError):
        p.ingest(DOCS / "edge_corrupt.pdf")
    assert p.sql.stats()["documents"] == 0 and p.vectors.count() == 0


def test_single_huge_line_is_split():
    p = PyxonParser(build_raptor=False)
    r = p.ingest(DOCS / "edge_one_line.txt")
    assert len(r.chunks) >= 40 and max(c.token_count for c in r.chunks) <= 120
