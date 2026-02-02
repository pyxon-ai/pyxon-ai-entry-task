"""
Content analysis and chunking strategy selection.
Analyzes semantic content, document structure, topics, and key concepts
to determine fixed vs dynamic chunking.
"""

import re
from typing import Any


def analyze_content(
    raw_text: str,
    pages_or_sections: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Analyze document content and choose chunking strategy.
    Returns: {"strategy": "fixed" | "dynamic", "params": dict}.
    Heuristics: headings, section length variance, list-like structure, document length.
    """
    if not raw_text or not raw_text.strip():
        return {"strategy": "fixed", "params": {"chunk_size": 512, "overlap": 50}}

    text = raw_text.strip()
    sections = pages_or_sections or [{"text": text}]
    section_texts = [s.get("text", "") or "" for s in sections if s.get("text")]

    # Heuristics for structure
    heading_pattern = re.compile(r"^(#{1,6}\s+|\d+\.\s+[A-Za-z\u0600-\u06FF]|[A-Za-z\u0600-\u06FF][^.\n]{0,50}:)\s*", re.MULTILINE)
    heading_count = len(heading_pattern.findall(text))

    # Section length variance: high variance suggests dynamic (chapters vs short sections)
    lengths = [len(s.strip()) for s in section_texts if s.strip()]
    if len(lengths) >= 2:
        mean_len = sum(lengths) / len(lengths)
        variance = sum((x - mean_len) ** 2 for x in lengths) / len(lengths)
        high_variance = variance > (mean_len * 2) ** 2
    else:
        high_variance = False

    # Many headings or high section variance -> dynamic (e.g. books with chapters)
    many_headings = heading_count >= 3
    num_sections = len([s for s in section_texts if s.strip()])
    has_structure = many_headings or (num_sections >= 5 and high_variance)

    if has_structure:
        strategy = "dynamic"
        params = {
            "split_on": "sections",  # use pages_or_sections as boundaries
            "min_chunk_chars": 100,
            "max_chunk_chars": 1500,
        }
    else:
        strategy = "fixed"
        params = {
            "chunk_size": 512,   # token-like (approx chars / 4)
            "overlap": 50,
            "min_chunk_chars": 50,
        }

    return {"strategy": strategy, "params": params}
