from typing import Optional

import docx
import os
from app.utils.arabic_cleaner import normalize_arabic_text

def load_document(file_path: str) -> str:
    """
    Load document content from PDF, DOCX, or TXT files.
    Preserves Arabic text and diacritics.
    """

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    text = ""
    if file_path.lower().endswith(".pdf"):
        text = _load_pdf(file_path)

    elif file_path.lower().endswith(".docx"):
        text = _load_docx(file_path)

    elif file_path.lower().endswith(".txt"):
        text = _load_txt(file_path)

    else:
        raise ValueError("Unsupported file format")

    return normalize_arabic_text(text)


import fitz  # PyMuPDF

def _load_pdf(path: str) -> str:
    text = []
    with fitz.open(path) as doc:
        for page in doc:
            # Usage of "blocks" helps preserve paragraph order better than raw "text"
            blocks = page.get_text("blocks")
            # Sort blocks based on coordinates:
            # Primary sort: Vertical position (y0), Top to Bottom
            # Secondary sort: Horizontal position (x0), Right to Left for Arabic context
            # Note: For strict RTL, we might want x1 descending, but standard practice often uses x0.
            # Let's use the user's suggested lambda: (b[1], -b[0]) -> y0 ascending, x0 descending (Right to Left)
            blocks.sort(key=lambda b: (b[1], -b[0])) 
            for b in blocks:
                # b[4] contains the text of the block
                if b[4].strip():
                    text.append(b[4])
    return "\n".join(text)


def _load_docx(path: str) -> str:
    doc = docx.Document(path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


def _load_txt(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
