"""File loaders for PDF, DOCX, DOC and TXT.

Every loader returns a :class:`ParsedDocument` made of ``Block`` objects.
A block is a paragraph-level unit that remembers whether the source format
marked it as a heading (DOCX heading styles, large PDF fonts are not used
because pypdf does not expose them reliably) and which page it came from.
"""
from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from .arabic import fix_presentation_forms, strip_diacritics

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".md"}


@dataclass
class Block:
    text: str
    is_heading: bool = False
    heading_level: int = 0
    page: int | None = None


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
        # A markdown heading or a short line followed by text stays its own block.
        if stripped.startswith("#"):
            flush()
            blocks.append(Block(text=stripped, page=page))
            continue
        buf.append(stripped)
    flush()
    return blocks


def decode_text(data: bytes) -> tuple[str, str]:
    """Decode TXT bytes, trying the encodings Arabic files are usually saved in."""
    if data.startswith(b"\xef\xbb\xbf"):
        return data[3:].decode("utf-8"), "utf-8-sig"
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16"), "utf-16"
    for enc in ("utf-8", "cp1256", "iso-8859-6"):
        try:
            return data.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace"), "utf-8 (lossy)"


def load_txt(path: Path, data: bytes) -> ParsedDocument:
    text, encoding = decode_text(data)
    return ParsedDocument(
        filename=path.name,
        file_type="txt",
        blocks=_split_paragraphs(text),
        sha256=_sha256(data),
        meta={"encoding": encoding},
    )


_ARABIC_WORD_RE = re.compile(r"[\u0600-\u06FF]+")
_PDF_HEADING_RE = re.compile(r"^((ال)?(فصل|باب|قسم|مقدمة|خاتمة)\b|(chapter|section|part)\s+\w+)", re.I)


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


def load_docx(path: Path, data: bytes) -> ParsedDocument:
    import docx

    document = docx.Document(str(path))
    blocks: list[Block] = []
    for para in document.paragraphs:
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
    # Tables are flattened row by row so their content is still searchable.
    for table in document.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells if c.text.strip()]
            if cells:
                blocks.append(Block(text=" | ".join(cells)))
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


def load_document(path: str | Path) -> ParsedDocument:
    """Dispatch on file extension."""
    path = Path(path)
    ext = path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFileType(f"Unsupported file type: {ext or '(none)'}")
    data = path.read_bytes()
    loader = {
        ".pdf": load_pdf,
        ".docx": load_docx,
        ".doc": load_doc,
        ".txt": load_txt,
        ".md": load_txt,
    }[ext]
    return loader(path, data)
