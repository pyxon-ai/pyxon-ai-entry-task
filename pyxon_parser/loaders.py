"""File loaders for PDF, DOCX, DOC and TXT.

Every loader returns a :class:`ParsedDocument` made of ``Block`` objects.
A block is a paragraph-level unit that remembers whether the source format
marked it as a heading (DOCX heading styles, large PDF fonts are not used
because pypdf does not expose them reliably) and which page it came from.
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import tempfile
from collections import Counter
from functools import lru_cache
from dataclasses import dataclass, field
from pathlib import Path

import logging

from .arabic import fix_presentation_forms, strip_diacritics

logging.getLogger("pypdf").setLevel(logging.ERROR)  # e.g. "EOF marker not found" on damaged files

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".md"}


@dataclass
class Block:
    text: str
    is_heading: bool = False
    heading_level: int = 0
    page: int | None = None
    is_table: bool = False


@dataclass
class ParsedDocument:
    filename: str
    file_type: str
    blocks: list[Block]
    sha256: str
    num_pages: int | None = None
    meta: dict = field(default_factory=dict)

    @property
    def text(self) -> str:
        return "\n\n".join(b.text for b in self.blocks)


class UnsupportedFileType(ValueError):
    pass


class DocumentLoadError(ValueError):
    """The file exists but cannot be parsed (damaged, wrong extension, encrypted...)."""


class EmptyDocumentError(ValueError):
    """The file was read but contains no extractable text (e.g. a scanned PDF without OCR)."""


# Lines that open a new structural unit: chapters, parts, sections, legal articles.
# Matched against diacritic-free text. The keyword must be followed by a number/ordinal,
# so a form field such as "القسم: المالية" is not mistaken for a heading.
STRUCTURAL_HEADING_RE = re.compile(
    r"^((ال)?(فصل|باب|قسم|جزء|مبحث|ماده|مادة)\s*[(\[]?\s*[^:\s()]+"
    r"|(ال)?(مقدمة|مقدمه|خاتمة|خاتمه)\b"
    r"|(chapter|section|part|article|appendix)\s+[\w.()]+)",
    re.I,
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _split_paragraphs(text: str, page: int | None = None) -> list[Block]:
    """Split raw text into paragraph blocks on blank lines (keeps short heading-like lines separate)."""
    blocks: list[Block] = []
    buf: list[str] = []

    def flush():
        if buf:
            para = " ".join(s.strip() for s in buf if s.strip())
            if para:
                blocks.append(Block(text=para, page=page))
            buf.clear()

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            flush()
            continue
        # Markdown headings and structural lines ("المادة 3: ...", "Chapter 2") start their own block
        # even when the paragraph follows on the next line without a blank line.
        if stripped.startswith("#") or (
            len(stripped.split()) <= 12
            and not stripped.endswith((".", "!", "?", "\u061F", "\u060C", ","))
            and STRUCTURAL_HEADING_RE.match(strip_diacritics(stripped))
        ):
            flush()
            blocks.append(Block(text=stripped, page=page))
            continue
        buf.append(stripped)
    flush()
    return blocks


_LATIN1_LETTERS = re.compile("[\u00C0-\u00FF]")


def _arabic_plausibility(text: str) -> float:
    """Higher = more like real Arabic text. Accented Latin letters inside Arabic words are the
    signature of a wrong single-byte codec (e.g. ISO-8859-6 bytes read as Windows-1256)."""
    arabic = len(re.findall("[\u0621-\u064A]", text))
    latin1 = len(_LATIN1_LETTERS.findall(text))
    return arabic - 5 * latin1


def decode_text(data: bytes, encoding: str | None = None) -> tuple[str, str]:
    """Decode TXT bytes. Pass ``encoding`` to skip detection.

    BOMs decide first; valid UTF-8 wins next (random single-byte text is almost never valid
    UTF-8). Otherwise every legacy Arabic codec that decodes cleanly is scored for plausibility,
    because Windows-1256 accepts nearly any byte and would silently mis-decode ISO-8859-6.
    """
    if encoding:
        return data.decode(encoding), encoding
    if data.startswith(b"\xef\xbb\xbf"):
        return data[3:].decode("utf-8"), "utf-8-sig"
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16"), "utf-16"
    try:
        return data.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        pass
    candidates = []
    for enc in ("cp1256", "iso-8859-6"):
        try:
            text = data.decode(enc)
        except UnicodeDecodeError:
            continue
        candidates.append((_arabic_plausibility(text), enc, text))
    if candidates:
        _, enc, text = max(candidates, key=lambda c: c[0])
        return text, enc
    return data.decode("utf-8", errors="replace"), "utf-8 (lossy)"


def load_txt(path: Path, data: bytes, encoding: str | None = None) -> ParsedDocument:
    text, encoding = decode_text(data, encoding)
    return ParsedDocument(
        filename=path.name,
        file_type="txt",
        blocks=_split_paragraphs(text),
        sha256=_sha256(data),
        meta={"encoding": encoding},
    )


_ARABIC_WORD_RE = re.compile(r"[\u0600-\u06FF]+")
_PDF_HEADING_RE = STRUCTURAL_HEADING_RE


def arabic_garble_score(text: str) -> float:
    """Share of Arabic 'words' that are a single base letter (+ marks).

    Correctly extracted Arabic has very few of these (mostly the conjunction
    و); text extracted in visual order or with broken ToUnicode maps falls
    apart into isolated letters. Used to pick the better PDF extractor per page.
    """
    words = [strip_diacritics(w) for w in _ARABIC_WORD_RE.findall(text)]
    words = [w for w in words if w]
    if len(words) < 5:
        return 0.0
    singles = sum(1 for w in words if len(w) == 1 and w not in "وبلك")
    return singles / len(words)


def _lines_to_blocks(lines: list[str], page: int) -> list[Block]:
    """Re-flow extractor lines into paragraphs (PDFs rarely contain blank lines)."""
    blocks: list[Block] = []
    buf: list[str] = []
    for line in (l.strip() for l in lines):
        if not line:
            if buf:
                blocks.append(Block(" ".join(buf), page=page))
                buf = []
            continue
        if _PDF_HEADING_RE.match(strip_diacritics(line)) and len(line.split()) <= 12:
            if buf:
                blocks.append(Block(" ".join(buf), page=page))
                buf = []
            blocks.append(Block(line, is_heading=True, heading_level=1, page=page))
            continue
        buf.append(line)
        if line.endswith((".", "!", "?", "؟", "۔")):
            blocks.append(Block(" ".join(buf), page=page))
            buf = []
    if buf:
        blocks.append(Block(" ".join(buf), page=page))
    return blocks


def _pymupdf_page_blocks(page, page_no: int, body_size: float) -> list[Block]:
    """Layout blocks with font-size based heading detection.

    PyMuPDF often puts a heading and the paragraph under it in one block, so
    lines are classified individually (heading = noticeably larger or bold
    short line) and consecutive lines of the same role are joined.
    """
    out: list[Block] = []
    for b in page.get_text("dict")["blocks"]:
        current: list[str] = []
        current_role: tuple[bool, int] | None = None
        for l in b.get("lines", []):
            text = "".join(s["text"] for s in l["spans"]).strip()
            if not text:
                continue
            size = max(s["size"] for s in l["spans"])
            bold = all(s["flags"] & 16 for s in l["spans"] if s["text"].strip())
            heading = len(text.split()) <= 14 and (size >= body_size + 1.5 or (bold and size >= body_size))
            role = (heading, (1 if size >= body_size + 3 else 2) if heading else 0)
            if current and (role != current_role or heading):
                out.append(Block(" ".join(current), current_role[0], current_role[1], page_no))
                current = []
            current.append(text)
            current_role = role
        if current:
            out.append(Block(" ".join(current), current_role[0], current_role[1], page_no))
    for blk in out:
        blk.text = fix_presentation_forms(blk.text)
    return out


def load_pdf(path: Path, data: bytes) -> ParsedDocument:
    """PDF loading with two extractors.

    PyMuPDF gives layout blocks and font sizes (-> real heading detection);
    pypdf is kept as a second opinion because for some Arabic PDFs it returns
    logical-order text where PyMuPDF does not. Per page we keep whichever
    output is less garbled according to :func:`arabic_garble_score`.
    """
    from pypdf import PdfReader

    reader = PdfReader(path)
    try:
        import pymupdf
    except ImportError:  # pragma: no cover - optional dependency
        pymupdf = None

    blocks: list[Block] = []
    extractor_used: list[str] = []
    mu_doc = pymupdf.open(path) if pymupdf else None
    body_size = 11.0
    if mu_doc is not None:
        sizes = Counter()
        for page in mu_doc:
            for b in page.get_text("dict")["blocks"]:
                for l in b.get("lines", []):
                    for s in l["spans"]:
                        sizes[round(s["size"])] += len(s["text"])
        if sizes:
            body_size = float(sizes.most_common(1)[0][0])

    for i, page in enumerate(reader.pages, start=1):
        # U+0000 shows up where some PDF fonts have no ToUnicode entry (e.g. shadda ligatures)
        pypdf_text = fix_presentation_forms(page.extract_text() or "").replace("\x00", "")
        candidates = []
        if mu_doc is not None:
            mu_blocks = _pymupdf_page_blocks(mu_doc[i - 1], i, body_size)
            candidates.append(("pymupdf", mu_blocks, arabic_garble_score(" ".join(b.text for b in mu_blocks))))
        candidates.append(("pypdf", _lines_to_blocks(pypdf_text.splitlines(), i), arabic_garble_score(pypdf_text)))
        # prefer PyMuPDF (richer layout) unless it is clearly more garbled
        name, page_blocks, score = candidates[0]
        if len(candidates) > 1 and candidates[1][2] + 0.05 < score:
            name, page_blocks, score = candidates[1]
        if mu_doc is not None and _needs_ocr(page_blocks, mu_doc[i - 1]):
            ocr_text = ocr_page(mu_doc[i - 1])
            if ocr_text:
                name, page_blocks = "ocr", _lines_to_blocks(ocr_text.splitlines(), i)
        blocks.extend(page_blocks)
        extractor_used.append(name)

    meta = {}
    if reader.metadata:
        meta = {k.strip("/"): str(v) for k, v in reader.metadata.items() if v}
    meta["extractor_per_page"] = extractor_used
    return ParsedDocument(
        filename=path.name,
        file_type="pdf",
        blocks=blocks,
        sha256=_sha256(data),
        num_pages=len(reader.pages),
        meta=meta,
    )


# -- OCR for scanned pages -----------------------------------------------------
OCR_LANG = os.getenv("PYXON_OCR_LANG", "ara+eng")


@lru_cache(maxsize=1)
def ocr_available() -> bool:
    """True when OCR can run: pytesseract installed, the tesseract binary on PATH (or at
    TESSERACT_CMD) and the Arabic language data present. Disable with PYXON_OCR=0."""
    if os.getenv("PYXON_OCR", "1") == "0":
        return False
    try:
        import pytesseract
    except ImportError:
        return False
    if os.getenv("TESSERACT_CMD"):
        pytesseract.pytesseract.tesseract_cmd = os.environ["TESSERACT_CMD"]
    elif os.name == "nt" and not shutil.which("tesseract"):
        default = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
        if default.exists():
            pytesseract.pytesseract.tesseract_cmd = str(default)
    try:
        langs = set(pytesseract.get_languages(config=""))
    except Exception:
        return False
    return all(lang in langs for lang in OCR_LANG.split("+"))


def _needs_ocr(page_blocks: list, mu_page) -> bool:
    """A page with (almost) no text layer but with images is a scan."""
    text_len = sum(len(b.text.strip()) for b in page_blocks)
    return text_len < 20 and bool(mu_page.get_images()) and ocr_available()


def ocr_page(mu_page, dpi: int = 300) -> str:
    """Render one PDF page and read it with Tesseract (Arabic + English by default). Tesseract
    returns Arabic in logical order, so the text indexes like any other page."""
    import io

    import pytesseract
    from PIL import Image

    pix = mu_page.get_pixmap(dpi=dpi)
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    text = pytesseract.image_to_string(img, lang=OCR_LANG, config="--psm 6")
    # drop the bidi control marks (LRM/RLM/embeddings) Tesseract puts around mixed-direction text
    text = re.sub("[\u200e\u200f\u202a-\u202e\u2066-\u2069]", "", text)
    lines = [ln.strip() for ln in text.splitlines()]
    text = "\n".join(ln for ln in lines if ln)
    # a blank or purely graphical page makes Tesseract emit a few stray letters: treat as no text
    return text if sum(ch.isalpha() for ch in text) >= 10 else ""


def _table_to_text(table) -> str:
    """One sentence per row, each value labelled with its column header.

    "Leave type: Annual, Days per year: 21, Paid: Yes." keeps row boundaries (the sentence
    splitter cuts on the full stop) and lets a question about a single cell match its header.
    """
    rows = []
    for row in table.rows:
        cells, seen = [], set()
        for c in row.cells:  # merged cells repeat; keep each once
            if id(c._tc) not in seen:
                seen.add(id(c._tc))
                cells.append(c.text.strip())
        if any(cells):
            rows.append(cells)
    if not rows:
        return ""
    header = rows[0] if len(rows) > 1 and all(rows[0]) else None
    out = []
    for cells in rows[1:] if header else rows:
        if header and len(cells) == len(header):
            out.append(", ".join(f"{h}: {v}" for h, v in zip(header, cells) if v) + ".")
        else:
            out.append(" | ".join(v for v in cells if v) + ".")
    return " ".join(out)


def load_docx(path: Path, data: bytes) -> ParsedDocument:
    import docx

    from docx.table import Table
    from docx.text.paragraph import Paragraph

    document = docx.Document(str(path))
    blocks: list[Block] = []
    # Walk the body in document order so a table stays under the heading it belongs to.
    for el in document.element.body.iterchildren():
        tag = el.tag.rsplit("}", 1)[-1]
        if tag == "p":
            para = Paragraph(el, document)
            text = para.text.strip()
            if not text:
                continue
            style = (para.style.name or "").lower() if para.style is not None else ""
            level = 0
            if style.startswith("heading"):
                try:
                    level = int(style.split()[-1])
                except ValueError:
                    level = 1
            elif style == "title":
                level = 1
            blocks.append(Block(text=text, is_heading=level > 0, heading_level=level))
        elif tag == "tbl":
            table_text = _table_to_text(Table(el, document))
            if table_text:
                blocks.append(Block(text=table_text, is_table=True))
    props = document.core_properties
    meta = {k: v for k, v in {"title": props.title, "author": props.author}.items() if v}
    return ParsedDocument(
        filename=path.name, file_type="docx", blocks=blocks, sha256=_sha256(data), meta=meta
    )


def find_soffice() -> str | None:
    """LibreOffice binary: PATH first, then the default Windows/macOS install locations."""
    found = shutil.which("soffice") or shutil.which("libreoffice")
    if found:
        return found
    for candidate in (
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
    ):
        if Path(candidate).exists():
            return candidate
    return None


def load_doc(path: Path, data: bytes) -> ParsedDocument:
    """Legacy .doc: convert to .docx with LibreOffice (headless), then reuse the DOCX loader."""
    soffice = find_soffice()
    if not soffice:
        raise UnsupportedFileType(
            ".doc files need LibreOffice installed (soffice) for conversion; "
            "please install it or save the file as .docx"
        )
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(
            [soffice, "--headless", "--convert-to", "docx", "--outdir", tmp, str(path)],
            check=True,
            capture_output=True,
            timeout=120,
        )
        converted = Path(tmp) / (path.stem + ".docx")
        parsed = load_docx(converted, converted.read_bytes())
    parsed.filename, parsed.file_type, parsed.sha256 = path.name, "doc", _sha256(data)
    return parsed


def load_document(path: str | Path, encoding: str | None = None) -> ParsedDocument:
    """Dispatch on file extension. ``encoding`` overrides detection for TXT/MD files."""
    path = Path(path)
    ext = path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFileType(f"Unsupported file type: {ext or '(none)'}")
    data = path.read_bytes()
    if not data.strip():
        raise EmptyDocumentError(f"{path.name} is empty.")
    loader = {
        ".pdf": load_pdf,
        ".docx": load_docx,
        ".doc": load_doc,
        ".txt": load_txt,
        ".md": load_txt,
    }[ext]
    try:
        parsed = loader(path, data, encoding) if ext in (".txt", ".md") else loader(path, data)
    except (UnsupportedFileType, EmptyDocumentError):
        raise
    except Exception as exc:  # damaged file, wrong extension, encrypted PDF ...
        raise DocumentLoadError(
            f"Could not read {path.name}: the file looks damaged or is not a valid {ext[1:].upper()} file "
            f"({type(exc).__name__})."
        ) from exc
    if not parsed.text.strip():
        if ext != ".pdf":
            hint = ""
        elif ocr_available():
            hint = " It looks like a scanned/image-only PDF and OCR found no readable text in it."
        else:
            hint = (" It looks like a scanned/image-only PDF; install Tesseract with Arabic data "
                    "(and `pip install pytesseract`) to read it with OCR.")
        raise EmptyDocumentError(f"No text could be extracted from {path.name}.{hint}")
    return parsed
