"""PDF text extraction. UTF-8, preserves Arabic diacritics (harakat)."""

from pathlib import Path
from typing import Any

from pypdf import PdfReader


def extract(path: str | Path) -> dict[str, Any]:
    """
    Extract text from a PDF file.
    Returns: {"raw_text": str, "pages_or_sections": list[dict]} with page-level structure.
    Preserves UTF-8 and Arabic diacritics.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected .pdf file, got {path.suffix}")

    reader = PdfReader(str(path))
    pages_or_sections: list[dict[str, Any]] = []
    raw_parts: list[str] = []

    for i, page in enumerate(reader.pages):
        # get_extract_text returns str; ensure we don't lose encoding
        text = page.extract_text() or ""
        # Preserve as-is for UTF-8 and diacritics
        raw_parts.append(text)
        pages_or_sections.append({"page": i + 1, "text": text})

    raw_text = "\n\n".join(raw_parts)
    return {"raw_text": raw_text, "pages_or_sections": pages_or_sections}
