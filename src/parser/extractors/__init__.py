"""Document extractors: PDF, DOCX, TXT. UTF-8, preserve diacritics."""

from pathlib import Path

from src.parser.extractors.pdf_extractor import extract as extract_pdf
from src.parser.extractors.docx_extractor import extract as extract_docx
from src.parser.extractors.txt_extractor import extract as extract_txt


def get_extractor(extension: str):
    """
    Return the extractor callable for the given file extension.
    extension: e.g. ".pdf", ".docx", ".txt" (case-insensitive).
    """
    ext = (extension or "").lower().strip()
    if not ext.startswith("."):
        ext = f".{ext}"
    if ext == ".pdf":
        return extract_pdf
    if ext in (".docx", ".doc"):
        return extract_docx
    if ext == ".txt":
        return extract_txt
    raise ValueError(f"Unsupported extension: {extension}. Use .pdf, .docx, or .txt.")


def extract(path: str | Path) -> dict:
    """Dispatch to the appropriate extractor based on file path."""
    path = Path(path)
    ext = path.suffix
    extractor = get_extractor(ext)
    return extractor(path)


__all__ = ["get_extractor", "extract", "extract_pdf", "extract_docx", "extract_txt"]
