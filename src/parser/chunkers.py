"""
Fixed and dynamic chunking. Preserves UTF-8 and Arabic diacritics.
Returns list of {"text", "start", "end", "index"}.
"""

import re
from typing import Any


def chunk_fixed(text: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Fixed-size chunking with overlap. Sentence-boundary aware where possible.
    Preserves diacritics and UTF-8.
    """
    chunk_size = params.get("chunk_size", 512) * 4  # approx chars (4 chars per token)
    overlap = params.get("overlap", 50) * 4
    min_chunk = params.get("min_chunk_chars", 50) or 50

    text = text.strip()
    if not text:
        return []

    # Split into sentences (keep Arabic and diacritics)
    sentence_end = re.compile(r"(?<=[.!?\u061F\u06D4])\s+|\n+")
    parts = sentence_end.split(text)
    sentences = [p.strip() for p in parts if p.strip()]

    if not sentences:
        # Fallback: raw sliding window
        chunks = []
        start = 0
        idx = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk_text = text[start:end]
            if len(chunk_text.strip()) >= min_chunk:
                chunks.append({"text": chunk_text, "start": start, "end": end, "index": idx})
                idx += 1
            start = end - overlap if end < len(text) else len(text)
        return chunks

    chunks: list[dict[str, Any]] = []
    current: list[str] = []
    current_len = 0
    char_start = 0
    idx = 0

    for i, sent in enumerate(sentences):
        sent_len = len(sent) + 1
        if current_len + sent_len > chunk_size and current:
            chunk_text = " ".join(current)
            char_end = char_start + len(chunk_text)
            chunks.append({"text": chunk_text, "start": char_start, "end": char_end, "index": idx})
            idx += 1
            # Overlap: keep last few sentences
            overlap_len = 0
            overlap_sents: list[str] = []
            for s in reversed(current):
                if overlap_len + len(s) <= overlap:
                    overlap_sents.append(s)
                    overlap_len += len(s) + 1
                else:
                    break
            current = list(reversed(overlap_sents))
            current_len = sum(len(s) for s in current) + len(current) - 1
            char_start = char_end - current_len - 1
        current.append(sent)
        current_len += sent_len

    if current:
        chunk_text = " ".join(current)
        char_end = char_start + len(chunk_text)
        chunks.append({"text": chunk_text, "start": char_start, "end": char_end, "index": idx})

    return chunks


def chunk_dynamic(
    text: str,
    structure: list[dict[str, Any]],
    params: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Dynamic chunking using section boundaries (e.g. pages_or_sections).
    Preserves diacritics and UTF-8. May merge small sections up to max_chunk_chars.
    """
    min_chunk = params.get("min_chunk_chars", 100) or 100
    max_chunk = params.get("max_chunk_chars", 1500) or 1500

    if not structure:
        return chunk_fixed(text, {"chunk_size": max_chunk // 4, "overlap": 0, "min_chunk_chars": min_chunk})

    sections = [s.get("text", "") or "" for s in structure if s.get("text")]
    if not sections:
        return chunk_fixed(text, {"chunk_size": max_chunk // 4, "overlap": 0, "min_chunk_chars": min_chunk})

    chunks: list[dict[str, Any]] = []
    current: list[str] = []
    current_len = 0
    char_start = 0
    idx = 0
    pos = 0

    for sec in sections:
        sec_len = len(sec) + 2
        if current_len + sec_len > max_chunk and current:
            chunk_text = "\n\n".join(current)
            char_end = char_start + len(chunk_text)
            if len(chunk_text.strip()) >= min_chunk:
                chunks.append({"text": chunk_text, "start": char_start, "end": char_end, "index": idx})
                idx += 1
            current = []
            current_len = 0
            char_start = pos
        current.append(sec.strip())
        current_len += sec_len
        pos += len(sec) + 2

    if current:
        chunk_text = "\n\n".join(current)
        char_end = char_start + len(chunk_text)
        if len(chunk_text.strip()) >= min_chunk:
            chunks.append({"text": chunk_text, "start": char_start, "end": char_end, "index": idx})

    return chunks
