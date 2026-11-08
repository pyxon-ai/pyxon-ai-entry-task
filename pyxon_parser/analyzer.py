"""Content analysis and chunking-strategy selection.

The analyzer looks at a parsed document and answers three questions:

1. *What is its structure?* -> headings/sections, paragraph statistics,
   form-like "key: value" lines, tables.
2. *What is it about?* -> language, keywords, a short extractive summary.
3. *How should it be chunked?* -> ``fixed`` for uniform / form-like content,
   ``dynamic`` for content with real sections or strongly varying structure.

The decision is a transparent weighted score so it can be explained in the
UI ("why did you pick dynamic?") and tuned in the benchmark.
"""
from __future__ import annotations

import re
import statistics
from dataclasses import asdict, dataclass, field

from .arabic import arabic_ratio, detect_language, diacritic_density, strip_diacritics, text_direction
from .loaders import STRUCTURAL_HEADING_RE, Block, ParsedDocument
from .text import content_tokens, count_tokens, split_sentences, top_keywords

_HEADING_PATTERNS = [
    re.compile(r"^#{1,6}\s+\S"),  # markdown
    re.compile(r"^(chapter|section|part|appendix|article)\s+[\w\dIVXLC]+\b", re.I),
    # "الفصل الأول" / "الباب 2" (the keyword must be followed by a word, so a form field like "القسم: المالية" is not a heading)
    STRUCTURAL_HEADING_RE,
    re.compile(r"^(\d+(\.\d+)*|[IVXLC]+)[.)]?\s+\S"),  # "2.1 Title", "IV. Title"
]
_KV_RE = re.compile(r"^[^:：]{1,40}[:：]\s*\S")


@dataclass
class Section:
    title: str
    level: int
    blocks: list[Block] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n\n".join(b.text for b in self.blocks)


@dataclass
class DocumentAnalysis:
    language: str
    direction: str
    arabic_ratio: float
    diacritic_density: float
    has_diacritics: bool
    num_blocks: int
    num_tokens: int
    num_headings: int
    num_sections: int
    para_len_mean: float
    para_len_cv: float
    section_len_cv: float
    kv_ratio: float
    doc_type: str
    keywords: list[str]
    summary: str
    strategy: str
    strategy_score: float
    reasons: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def looks_like_heading(block: Block, next_block: Block | None) -> tuple[bool, int]:
    """Heuristic heading detection for formats without style information."""
    if block.is_heading:
        return True, block.heading_level or 1
    text = strip_diacritics(block.text.strip())  # harakat would break the regexes
    if text.startswith("#"):
        return True, len(text) - len(text.lstrip("#"))
    words = count_tokens(text)
    if words == 0 or words > 12 or text.endswith((".", "،", ",", ";", ":")):
        return False, 0
    if _KV_RE.match(text) and not _HEADING_PATTERNS[1].match(text) and not _HEADING_PATTERNS[2].match(text):
        return False, 0  # "Date: 2025-01-14" is a form field, not a heading
    for pat in _HEADING_PATTERNS[1:]:
        if pat.match(text):
            return True, 2 if re.match(r"^\d+\.\d+", text) else 1
    # Short title-like line followed by a much longer paragraph.
    if next_block is not None and words <= 8 and count_tokens(next_block.text) >= 3 * words + 10:
        if not text.endswith(("?", "؟", "!")):
            return True, 2
    return False, 0


def split_sections(doc: ParsedDocument) -> list[Section]:
    """Group blocks under their nearest preceding heading."""
    sections: list[Section] = [Section(title="", level=0)]
    blocks = doc.blocks
    for i, block in enumerate(blocks):
        nxt = blocks[i + 1] if i + 1 < len(blocks) else None
        is_h, level = looks_like_heading(block, nxt)
        if is_h:
            sections.append(Section(title=block.text.lstrip("# ").strip(), level=level))
        else:
            sections[-1].blocks.append(block)
    return [s for s in sections if s.blocks or s.title]


def _cv(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = statistics.fmean(values)
    return statistics.pstdev(values) / mean if mean else 0.0


def extractive_summary(text: str, max_sentences: int = 3) -> str:
    """Pick the sentences with the highest keyword coverage (keeps original diacritics)."""
    sentences = split_sentences(text)
    if len(sentences) <= max_sentences:
        return " ".join(sentences)
    keywords = set(top_keywords(text, k=20))
    scored = []
    for idx, s in enumerate(sentences):
        toks = content_tokens(s)
        if not toks:
            continue
        score = sum(t in keywords for t in toks) / (len(toks) ** 0.5)
        scored.append((score, idx, s))
    best = sorted(scored, reverse=True)[:max_sentences]
    return " ".join(s for _, _, s in sorted(best, key=lambda x: x[1]))


def form_summary(blocks: list[Block], max_fields: int = 8) -> str:
    """Describe a form/record document by its fields instead of stitching sentences from different records."""
    fields: dict[str, int] = {}
    for b in blocks:
        m = re.match(r"^([^:：]{1,40})[:：]", b.text)
        if m:
            key = m.group(1).strip()
            fields[key] = fields.get(key, 0) + 1
    if not fields:
        return ""
    n_records = max(fields.values())
    names = ", ".join(sorted(fields, key=lambda k: -fields[k])[:max_fields])
    return f"Structured document with about {n_records} records. Fields: {names}."


def analyze(doc: ParsedDocument) -> tuple[DocumentAnalysis, list[Section]]:
    text = doc.text
    sections = split_sections(doc)
    headings = [s for s in sections if s.title]
    body_blocks = [b for s in sections for b in s.blocks]
    para_lens = [count_tokens(b.text) for b in body_blocks] or [0]
    section_lens = [count_tokens(s.text) for s in sections if s.blocks]
    # tables render as "Header: value" rows; they are not evidence of a form document
    text_blocks = [b for b in body_blocks if not b.is_table] or body_blocks
    kv_ratio = sum(bool(_KV_RE.match(b.text)) for b in text_blocks) / max(len(text_blocks), 1)
    para_cv, section_cv = _cv(para_lens), _cv(section_lens)
    n_tokens = count_tokens(text)

    # ---- strategy score: >0 means dynamic, <=0 means fixed ----------------
    score, reasons = 0.0, []
    if len(headings) >= 2:
        score += 1.5
        reasons.append(f"{len(headings)} headings/sections detected -> structure-aware splitting keeps sections intact")
    elif len(headings) == 1:
        score += 0.3
        reasons.append("only one heading detected")
    else:
        score -= 0.5
        reasons.append("no headings detected")
    if para_cv > 0.75:
        score += 0.8
        reasons.append(f"paragraph lengths vary a lot (CV={para_cv:.2f})")
    elif para_cv < 0.45:
        score -= 0.6
        reasons.append(f"paragraph lengths are uniform (CV={para_cv:.2f})")
    if len(section_lens) >= 2 and section_cv > 0.5:
        score += 0.5
        reasons.append(f"sections have uneven lengths (CV={section_cv:.2f})")
    if kv_ratio > 0.3:
        score -= 1.5
        reasons.append(f"{kv_ratio:.0%} of lines are 'key: value' fields -> form / structured record")
    if n_tokens < 150:
        score -= 1.0
        reasons.append("document is very short")
    strategy = "dynamic" if score > 0 else "fixed"

    if kv_ratio > 0.3:
        doc_type = "form / structured report"
    elif len(headings) >= 3:
        doc_type = "book / multi-section document"
    elif len(headings) >= 1:
        doc_type = "article"
    else:
        doc_type = "plain text"

    density = diacritic_density(text)
    analysis = DocumentAnalysis(
        language=detect_language(text),
        direction=text_direction(text),
        arabic_ratio=round(arabic_ratio(text), 3),
        diacritic_density=round(density, 3),
        has_diacritics=density > 0.05,
        num_blocks=len(doc.blocks),
        num_tokens=n_tokens,
        num_headings=len(headings),
        num_sections=len(sections),
        para_len_mean=round(statistics.fmean(para_lens), 1),
        para_len_cv=round(para_cv, 3),
        section_len_cv=round(section_cv, 3),
        kv_ratio=round(kv_ratio, 3),
        doc_type=doc_type,
        keywords=top_keywords(text, k=12),
        summary=form_summary(body_blocks) if kv_ratio > 0.3 else extractive_summary("\n\n".join(b.text for b in body_blocks)),
        strategy=strategy,
        strategy_score=round(score, 2),
        reasons=reasons,
    )
    return analysis, sections
