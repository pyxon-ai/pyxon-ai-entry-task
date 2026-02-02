"""TXT text extraction. UTF-8, preserves Arabic diacritics (harakat)."""

from pathlib import Path
from typing import Any


def extract(path: str | Path) -> dict[str, Any]:
    """
    Extract text from a plain text file.
    Returns: {"raw_text": str, "pages_or_sections": list[dict]} with line/paragraph structure.
    Uses UTF-8 encoding; preserves diacritics. No BOM stripping that would break Arabic.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"TXT not found: {path}")
    if path.suffix.lower() != ".txt":
        raise ValueError(f"Expected .txt file, got {path.suffix}")

    with open(path, encoding="utf-8") as f:
        raw_text = f.read()

    # Build sections by paragraph (blank-line separated)
    paragraphs = [p.strip() for p in raw_text.split("\n\n") if p.strip()]
    pages_or_sections = [{"index": i, "text": p} for i, p in enumerate(paragraphs)]
    if not pages_or_sections and raw_text.strip():
        pages_or_sections = [{"index": 0, "text": raw_text.strip()}]

    return {"raw_text": raw_text, "pages_or_sections": pages_or_sections}
