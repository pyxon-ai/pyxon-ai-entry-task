"""Regression tests for the issues found in the independent review of PR #19.

Each test reproduces a reported failure with fresh inputs (not repository fixtures).
"""
from __future__ import annotations

import gc
from pathlib import Path
import os

import pytest

os.environ.setdefault("PYXON_EMBEDDER", "hashing")

from docx import Document  # noqa: E402

from pyxon_parser import PyxonParser  # noqa: E402
from pyxon_parser.analyzer import Section, analyze  # noqa: E402
from pyxon_parser.chunking import DynamicChunker, FixedChunker  # noqa: E402
from pyxon_parser.embeddings import HashingEmbedder  # noqa: E402
from pyxon_parser.loaders import Block, EmptyDocumentError, decode_text, load_document  # noqa: E402
from pyxon_parser.storage import SQLStore  # noqa: E402

AR = "مَرْحَبًا بِالْعَالَمِ. يعمل سامر في قسم الشبكات."


@pytest.fixture
def en_ar_files(tmp_path):
    en = tmp_path / "en.txt"
    en.write_text("The zephyr observatory opens at seven. Tickets cost twelve dinars.", encoding="utf-8")
    ar = tmp_path / "ar.txt"
    ar.write_text(AR, encoding="utf-8")
    return en, ar


# --- 1. store isolation ------------------------------------------------------------------
def test_new_inmemory_parsers_never_inherit_vectors(tmp_path):
    src = tmp_path / "sentinel.txt"
    src.write_text("Unique sentinel belongs only to its original parser.", encoding="utf-8")
    for _ in range(40):  # object ids get reused quickly; the old id()-based names collided
        p = PyxonParser(embedder=HashingEmbedder(), build_raptor=False)
        assert p.vectors.count() == 0 and p.sql.stats()["documents"] == 0
        p.ingest(src)
        del p
        gc.collect()


def test_close_drops_private_collection(tmp_path):
    src = tmp_path / "a.txt"
    src.write_text("Some text about closing parsers properly.", encoding="utf-8")
    with PyxonParser(build_raptor=False) as p:
        p.ingest(src)
        name, client = p.vectors.collection.name, p.vectors.client
    assert name not in [c.name for c in client.list_collections()]


# --- 2. atomic writes ----------------------------------------------------------------------
def _fail(*_a, **_k):
    raise RuntimeError("simulated vector store failure")


def test_failed_vector_write_leaves_nothing_behind(tmp_path, en_ar_files):
    en, _ = en_ar_files
    p = PyxonParser(data_dir=tmp_path / "db")
    p.vectors.add = _fail
    with pytest.raises(RuntimeError):
        p.ingest(en)
    stats = p.sql.stats()
    assert stats["documents"] == stats["leaf_chunks"] == stats["terms"] == 0
    assert p.vectors.count() == 0


def test_failed_replacement_keeps_previous_version(tmp_path, en_ar_files):
    en, _ = en_ar_files
    p = PyxonParser(data_dir=tmp_path / "db")
    old = p.ingest(en)
    good_add = p.vectors.add
    p.vectors.add = _fail
    with pytest.raises(RuntimeError):
        p.ingest(en)  # same sha256 -> replacement
    p.vectors.add = good_add
    assert p.sql.get_document(old.document_id) is not None
    assert p.search("zephyr observatory", k=1)[0].filename == "en.txt"


def test_successful_replacement_swaps_versions(tmp_path, en_ar_files):
    en, _ = en_ar_files
    p = PyxonParser(data_dir=tmp_path / "db")
    first = p.ingest(en)
    second = p.ingest(en)
    assert p.sql.get_document(first.document_id) is None
    assert p.sql.stats()["documents"] == 1
    assert p.vectors.count() == p.sql.chunk_count()
    assert {h.document_id for h in p.search("zephyr", k=5)} == {second.document_id}


# --- 3. dynamic chunking invariants --------------------------------------------------------
def test_short_section_keeps_its_own_heading():
    sections = [
        Section("Fees", 1, [Block("Annual fee is 75 dinars.")]),
        Section("Refunds", 1, [Block("Refunds are available during the first fourteen days after purchase. "
                                     "Keep your original receipt and contact the customer service team.")]),
    ]
    chunks = DynamicChunker(HashingEmbedder()).chunk(sections)
    fees = [c for c in chunks if "75 dinars" in c.text]
    assert fees and all(c.section == "Fees" for c in fees)
    assert all("75 dinars" not in c.text for c in chunks if c.section == "Refunds")


@pytest.mark.parametrize("words", [221, 300, 441, 1000])
def test_dynamic_chunks_never_exceed_max_size(words):
    sections = [Section("", 0, [Block(" ".join(["word"] * words))])]
    chunks = DynamicChunker(HashingEmbedder(), max_size=220).chunk(sections)
    assert all(c.token_count <= 220 for c in chunks)
    assert sum(c.token_count for c in chunks) == words


def test_dynamic_chunk_pages_follow_their_sentences():
    long = " ".join(f"Sentence number {i} talks about topic {i % 7}." for i in range(80))
    sections = [Section("S", 1, [Block(long, page=1), Block(long, page=2)])]
    chunks = DynamicChunker(HashingEmbedder(), max_size=120).chunk(sections)
    assert {c.page for c in chunks} == {1, 2}


# --- 4. DOCX body order ---------------------------------------------------------------------
def test_docx_table_stays_under_its_heading(tmp_path):
    d = Document()
    d.add_heading("Product Alpha", 1)
    d.add_paragraph("Alpha is the basic product.")
    t = d.add_table(rows=2, cols=2)
    t.cell(0, 0).text, t.cell(0, 1).text = "Item", "Price"
    t.cell(1, 0).text, t.cell(1, 1).text = "Alpha", "17 dinars"
    d.add_heading("Product Beta", 1)
    d.add_paragraph("Beta is the premium product.")
    f = tmp_path / "table_order.docx"
    d.save(f)
    _, sections = analyze(load_document(f))
    alpha = next(s for s in sections if s.title == "Product Alpha")
    beta = next(s for s in sections if s.title == "Product Beta")
    assert "Item: Alpha, Price: 17 dinars." in alpha.text
    assert "17 dinars" not in beta.text


# --- 5. SQL routing ------------------------------------------------------------------------------
@pytest.fixture
def routed(tmp_path, en_ar_files):
    p = PyxonParser(data_dir=tmp_path / "db")
    for f in en_ar_files:
        p.ingest(f)
    p.rag.llm = None
    return p


@pytest.mark.parametrize("q", ["Which documents are Arabic?", "List Arabic documents", "ما هي الملفات العربية؟"])
def test_language_filter_lists_only_arabic(routed, q):
    ans = routed.ask(q)
    assert ans.route == "sql" and [r["filename"] for r in ans.rows] == ["ar.txt"]


@pytest.mark.parametrize("q", ["How many Arabic documents are indexed?", "كم عدد المستندات المكتوبة بالعربية؟"])
def test_language_filter_counts(routed, q):
    ans = routed.ask(q)
    assert ans.route == "sql" and ans.rows == [{"documents": 1}]


@pytest.mark.parametrize("q", [
    "What is the marketing strategy for Zephyr?",
    "Which documents mention the observatory?",
    "When does the zephyr observatory open?",
])
def test_content_questions_are_not_routed_to_sql(routed, q):
    assert routed.ask(q).route == "rag"


def test_strategy_question_and_doc_scope(routed):
    ans = routed.ask("Which chunking strategy was used?")
    assert ans.route == "sql" and len(ans.rows) == 2
    ar_id = next(d["id"] for d in routed.sql.list_documents() if d["filename"] == "ar.txt")
    scoped = routed.ask("How many documents are indexed?", doc_ids=[ar_id])
    assert scoped.rows == [{"documents": 1}]


# --- 6. embedding model change on an existing index ----------------------------------------------
def test_switching_embedder_rebuilds_vectors(tmp_path, en_ar_files):
    p = PyxonParser(data_dir=tmp_path / "db")
    for f in en_ar_files:
        p.ingest(f)
    other = PyxonParser(data_dir=tmp_path / "db", embedder=HashingEmbedder(dim=384))
    assert other.vectors.count() == other.sql.chunk_count()
    assert other.search("zephyr observatory", k=1)[0].filename == "en.txt"
    # the original model's vectors are untouched and still usable
    again = PyxonParser(data_dir=tmp_path / "db")
    assert again.search("zephyr observatory", k=1)[0].filename == "en.txt"


# --- additional gaps ---------------------------------------------------------------------------
@pytest.mark.parametrize("enc", ["utf-8", "utf-16", "cp1256", "iso-8859-6"])
def test_arabic_encodings_roundtrip(enc):
    text, detected = decode_text(AR.encode(enc))
    assert text == AR and detected.startswith(enc.split("-sig")[0])


def test_encoding_override(tmp_path):
    f = tmp_path / "legacy.txt"
    f.write_bytes(AR.encode("iso-8859-6"))
    assert load_document(f, encoding="iso-8859-6").text == AR


def test_heading_only_file_raises_clear_error(tmp_path):
    f = tmp_path / "headings.txt"
    f.write_text("# Safety\n\n# Emergency contacts\n", encoding="utf-8")
    p = PyxonParser()
    with pytest.raises(EmptyDocumentError):
        p.ingest(f)
    assert p.sql.stats()["documents"] == 0


@pytest.mark.parametrize("sql", [
    "WITH x AS (SELECT 1) DELETE FROM documents RETURNING id",
    "WITH x AS (SELECT 1) UPDATE documents SET filename = 'x' RETURNING id",
    "SELECT * FROM documents; DROP TABLE documents",
])
def test_readonly_guard_blocks_mutations(sql):
    s = SQLStore(":memory:")
    s.conn.execute("INSERT INTO documents(filename, file_type, sha256) VALUES ('sentinel','txt','x')")
    s.conn.commit()
    with pytest.raises(ValueError):
        s.run_readonly_query(sql)
    assert s.conn.execute("SELECT filename FROM documents").fetchone()[0] == "sentinel"


def test_extractive_answer_drops_unrelated_sentences(tmp_path):
    center = tmp_path / "center.txt"
    center.write_text("يفتح مركز نور الثقافي أبوابه في الساعة التاسعة صباحاً. ويقدم المركز دورات في الخط العربي.",
                      encoding="utf-8")
    staff = tmp_path / "staff.txt"
    staff.write_text("الاسم: نور الهدى سالم. القسم: تقنية المعلومات. المدينة: عمان.", encoding="utf-8")
    p = PyxonParser()
    p.rag.llm = None
    p.ingest(center)
    p.ingest(staff)
    ans = p.ask("متى يفتح مركز نور؟").answer
    assert "التاسعة" in ans and "الهدى" not in ans


def test_unanswerable_question_says_not_found(routed):
    assert "could not find" in routed.ask("What is the capital of Peru?").answer


def test_boundary_metric_rejects_forced_cuts():
    from benchmarks.run_benchmark import _chunk_quality

    sections = [Section("", 0, [Block(" ".join(["ordinary"] * 300))])]
    chunks = FixedChunker(120, 20).chunk(sections)
    assert _chunk_quality(chunks, sections, HashingEmbedder())["clean_boundary_rate"] < 1


def test_same_passage_from_two_files_is_shown_once():
    from pathlib import Path

    samples = Path(__file__).resolve().parent.parent / "samples"
    p = PyxonParser()
    p.ingest(samples / "water_ar.txt")
    p.ingest(samples / "water_ar.pdf")  # same book; the PDF copy lost some shadda marks
    from pyxon_parser.arabic import normalize_for_index

    def answering(hits):
        return [h for h in hits if "علامات الجفاف" in normalize_for_index(h.text)]

    collapsed = answering(p.search("ما هي علامات الجفاف؟", k=5))
    assert len(collapsed) == 1
    assert {collapsed[0].filename, *collapsed[0].also_in} == {"water_ar.txt", "water_ar.pdf"}
    assert len(answering(p.search("ما هي علامات الجفاف؟", k=5, collapse_duplicates=False))) == 2
    # whichever copy ranks first, the fully vocalized TXT text is the one shown
    top = p.search("حَيٌّ", k=1)[0]
    assert top.filename == "water_ar.txt" and "حَيٌّ" in top.text and top.also_in == ["water_ar.pdf"]


def test_broken_plural_matches_singular():
    """'المطر' (rain) must find a passage that only says 'الأمطار' (af'al broken plural)."""
    from pyxon_parser.text import broken_plural_singular, content_tokens

    assert broken_plural_singular("امطار") == "مطر"
    assert broken_plural_singular("انهار") == "نهر"
    assert broken_plural_singular("مطار") is None  # airport: not the pattern
    assert "مطر" in content_tokens("وَتَسْقُطُ الْأَمْطَارُ")
    p = PyxonParser(build_raptor=False)
    for name in ["water_ar.txt", "coffee_history.docx", "inspection_report.txt"]:
        p.ingest(Path(__file__).resolve().parent.parent / "samples" / name)
    top = p.search("من أين يأتي المطر؟", k=3)[0]
    assert top.filename == "water_ar.txt" and "keyword" in top.sources


def test_stale_keyword_index_is_rebuilt_on_open(tmp_path):
    """A store built by an older tokenizer is re-tokenized on open: unchanged files are skipped on
    re-upload, so without this the new tokens (e.g. 'مطر' for 'الأمطار') would never reach them."""
    samples = Path(__file__).resolve().parent.parent / "samples"
    p = PyxonParser(data_dir=tmp_path, build_raptor=False)
    p.ingest(samples / "water_ar.txt")
    p.ingest(samples / "coffee_history.docx")
    # simulate an index written by the previous tokenizer: no singular tokens, old version number
    p.sql.conn.execute("UPDATE chunks_fts SET tokens = replace(tokens, ' مطر', ''), stems = ''")
    p.sql.set_lexical_version(1)
    assert not p.sql.keyword_search(["مطر"], k=5)
    p.close()
    p2 = PyxonParser(data_dir=tmp_path, build_raptor=False)
    from pyxon_parser.text import LEXICAL_VERSION

    assert p2.sql.lexical_version() == LEXICAL_VERSION
    assert p2.sql.keyword_search(["مطر"], k=5)
    assert p2.search("من أين يأتي المطر؟", k=3)[0].filename == "water_ar.txt"
    assert p2.sql.conn.execute("SELECT count(*) FROM terms").fetchone()[0] > 0
    p2.close()


def test_light_stemming_and_weighted_stem_column(tmp_path):
    """Arabic surface forms share a stem in the second FTS column; exact words still rank first."""
    from pyxon_parser.text import index_fields, light_stem

    assert light_stem("معلمون") == "معلم" and light_stem("للمدارس") == "مدارس"
    words, stems = index_fields("ذهب المعلمون إلى المدارس")
    assert "معلمون" in words.split() and "معلم" in stems.split()
    p = PyxonParser(build_raptor=False)
    for name, text in [("a.txt", "حضر المعلم الاجتماع الصباحي في القاعة الكبرى."),
                       ("b.txt", "حضر المعلمون الاجتماع المسائي في الساحة.")]:
        (tmp_path / name).write_text(text, encoding="utf-8")
        p.ingest(tmp_path / name)
    hits = p.sql.keyword_search(["معلمون", "معلم"], k=5)
    names = [p.sql.get_chunks([cid])[cid]["filename"] for cid, _ in hits]
    assert names[0] == "b.txt" and "a.txt" in names  # exact form first, stem-only match still found


def test_old_single_column_fts_store_is_migrated(tmp_path):
    """A store created before the stems column existed is migrated on open."""
    import sqlite3

    samples = Path(__file__).resolve().parent.parent / "samples"
    p = PyxonParser(data_dir=tmp_path, build_raptor=False)
    p.ingest(samples / "water_ar.txt")
    p.close()
    con = sqlite3.connect(tmp_path / "pyxon.sqlite3")
    con.execute("DROP TABLE chunks_fts")
    con.execute("CREATE VIRTUAL TABLE chunks_fts USING fts5(chunk_id UNINDEXED, document_id UNINDEXED, level UNINDEXED, tokens)")
    con.execute("PRAGMA user_version = 2")
    con.commit()
    con.close()
    p2 = PyxonParser(data_dir=tmp_path, build_raptor=False)
    assert p2.search("من أين يأتي المطر؟", k=1)[0].filename == "water_ar.txt"
    p2.ingest(samples / "coffee_history.docx")  # new rows go into the new two-column table
    p2.close()


def test_scanned_pdf_is_read_with_ocr():
    """An image-only Arabic PDF goes through Tesseract and becomes searchable."""
    from pyxon_parser.loaders import ocr_available

    if not ocr_available():
        pytest.skip("Tesseract with Arabic data is not installed")
    samples = Path(__file__).resolve().parent.parent / "samples"
    doc = load_document(samples / "scanned_notice_ar.pdf")
    assert doc.meta["extractor_per_page"] == ["ocr"]
    assert "جبل الحسين" in doc.text and "‏" not in doc.text
    p = PyxonParser(build_raptor=False)
    p.ingest(samples / "scanned_notice_ar.pdf")
    p.ingest(samples / "water_ar.txt")
    assert "الثامنة" in p.ask("متى سيتم قطع المياه في جبل الحسين؟").answer


def test_image_without_text_still_rejected_clearly():
    """A blank scan gives a clear error whether or not OCR is installed."""
    heldout = Path(__file__).resolve().parent.parent / "benchmarks" / "heldout" / "docs"
    with pytest.raises(EmptyDocumentError, match="scanned/image-only PDF"):
        load_document(heldout / "edge_image_only.pdf")


def test_neural_models_get_text_without_harakat():
    """Vocalized and bare Arabic must reach a neural model as the same string (pretrained models
    saw almost only unvocalized text), and the vector collection name records that input format."""
    from pyxon_parser.embeddings import NEURAL_INPUT_VERSION, FastEmbedEmbedder, HashingEmbedder, neural_input

    voc, bare = "وَتَسْقُطُ الْأَمْطَارُ عَلَى الْجِبَالِ", "وتسقط الأمطار على الجبال"
    assert neural_input([voc]) == neural_input([bare]) == [bare]
    assert HashingEmbedder().index_key == HashingEmbedder().name
    fake = FastEmbedEmbedder.__new__(FastEmbedEmbedder)
    fake.name = "some/model"
    assert fake.index_key == f"some/model#{NEURAL_INPUT_VERSION}"


def test_duplicate_with_extra_title_line_is_collapsed():
    """The TXT copy of a chunk starts with the book title, the DOCX copy does not: still one result."""
    from pyxon_parser.retrieval import _same_passage

    body = "الماءهواساسالحياهعليسطحالارض" * 8
    assert _same_passage("كتابالماءواسراره" + body, body)
    assert not _same_passage(body, body[: len(body) // 2])  # half a passage is not a duplicate
    samples = Path(__file__).resolve().parent.parent / "samples"
    p = PyxonParser(build_raptor=False)
    for name in ["water_ar.txt", "water_ar.docx"]:
        p.ingest(samples / name)
    res = p.search("الماء هو أساس الحياة على سطح الأرض", k=5)
    files = [r.filename for r in res]
    assert len(files) == len(set(r.chunk_id for r in res))
    assert not any(a.text[:40] == b.text[:40] for i, a in enumerate(res) for b in res[i + 1:])
    assert res[0].also_in  # the other copy is listed, not shown twice


def test_already_indexed_file_is_skipped_before_parsing(monkeypatch):
    """replace=False must not re-parse an unchanged file (the demo re-loads its samples)."""
    import pyxon_parser.pipeline as pl

    samples = Path(__file__).resolve().parent.parent / "samples"
    p = PyxonParser(build_raptor=False)
    first = p.ingest(samples / "water_ar.pdf")
    monkeypatch.setattr(pl, "load_document", lambda *a, **k: (_ for _ in ()).throw(AssertionError("parsed again")))
    again = p.ingest(samples / "water_ar.pdf", replace=False)
    assert again.duplicate and again.document_id == first.document_id
