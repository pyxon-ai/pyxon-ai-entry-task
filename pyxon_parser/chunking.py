"""Fixed and dynamic chunking.

* **FixedChunker** - sliding window of ~``chunk_size`` words that only cuts on
  sentence boundaries and carries ``overlap`` words of context forward.
  Predictable sizes; ideal for uniform reports and forms.

* **DynamicChunker** - structure first, semantics second:
    1. every detected section (chapter, heading) becomes a candidate chunk;
    2. sections longer than ``max_size`` are split where the meaning shifts,
       i.e. where cosine similarity between neighbouring sentence windows
       drops below a document-relative threshold;
    3. fragments smaller than ``min_size`` are merged into a neighbour from
       the same section.
  Chunks therefore never straddle two chapters and rarely cut mid-topic.

Both chunkers keep the original text (diacritics included).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .analyzer import Section
from .arabic import normalize_for_index
from .embeddings import Embedder
from .text import count_tokens, split_sentences


@dataclass
class Chunk:
    text: str
    index: int = 0
    section: str = ""
    strategy: str = "fixed"
    page: int | None = None
    level: int = 0  # 0 = leaf chunk, >0 = RAPTOR summary level
    children: list[int] = field(default_factory=list)

    @property
    def token_count(self) -> int:
        return count_tokens(self.text)

    @property
    def normalized(self) -> str:
        return normalize_for_index(self.text)

    def embedding_text(self) -> str:
        """Section title gives the embedding context the chunk text may lack."""
        return f"{self.section}\n{self.text}" if self.section else self.text


def _units(sections: list[Section]) -> list[tuple[str, str, int | None]]:
    """(sentence, section_title, page) triples in reading order."""
    out = []
    for s in sections:
        for b in s.blocks:
            for sent in split_sentences(b.text):
                out.append((sent, s.title, b.page))
    return out


def _split_long_sentence(sentence: str, max_words: int) -> list[str]:
    words = sentence.split()
    return [" ".join(words[i : i + max_words]) for i in range(0, len(words), max_words)]


class FixedChunker:
    def __init__(self, chunk_size: int = 120, overlap: int = 20):
        if overlap >= chunk_size:
            raise ValueError("overlap must be smaller than chunk_size")
        self.chunk_size, self.overlap = chunk_size, overlap

    def chunk(self, sections: list[Section]) -> list[Chunk]:
        units: list[tuple[str, str, int | None]] = []
        for sent, title, page in _units(sections):
            if count_tokens(sent) > self.chunk_size:
                units.extend((p, title, page) for p in _split_long_sentence(sent, self.chunk_size))
            else:
                units.append((sent, title, page))

        chunks: list[Chunk] = []
        window: list[tuple[str, str, int | None]] = []
        size = 0
        for unit in units:
            n = count_tokens(unit[0])
            if window and size + n > self.chunk_size:
                chunks.append(self._make(window, len(chunks)))
                # carry trailing sentences (up to `overlap` words) into the next window
                carry, carried = [], 0
                for u in reversed(window):
                    c = count_tokens(u[0])
                    if carried + c > self.overlap:
                        break
                    carry.insert(0, u)
                    carried += c
                window, size = carry, carried
            window.append(unit)
            size += n
        if window:
            chunks.append(self._make(window, len(chunks)))
        return chunks

    @staticmethod
    def _make(window, index: int) -> Chunk:
        titles = [t for _, t, _ in window if t]
        return Chunk(
            text=" ".join(s for s, _, _ in window),
            index=index,
            section=titles[0] if titles else "",
            strategy="fixed",
            page=window[0][2],
        )


class DynamicChunker:
    def __init__(
        self,
        embedder: Embedder,
        min_size: int = 40,
        max_size: int = 220,
        window: int = 2,
        breakpoint_percentile: float = 20.0,
    ):
        self.embedder = embedder
        self.min_size, self.max_size = min_size, max_size
        self.window, self.breakpoint_percentile = window, breakpoint_percentile

    # -- semantic split ------------------------------------------------------
    def _pack(self, units: list[tuple[str, int | None]]) -> list[list[tuple[str, int | None]]]:
        """Greedy size-only grouping (used when there are too few units to measure topic shifts)."""
        groups, current, size = [], [], 0
        for unit in units:
            n = count_tokens(unit[0])
            if current and size + n > self.max_size:
                groups.append(current)
                current, size = [], 0
            current.append(unit)
            size += n
        if current:
            groups.append(current)
        return groups

    def _semantic_split(self, units: list[tuple[str, int | None]]) -> list[list[tuple[str, int | None]]]:
        """Split (sentence, page) units where meaning shifts, never exceeding ``max_size`` words."""
        if len(units) < 3:
            return self._pack(units)
        sentences = [u[0] for u in units]
        w = self.window
        windows = [" ".join(sentences[max(0, i - w + 1) : i + 1]) for i in range(len(sentences))]
        ahead = [" ".join(sentences[i : i + w]) for i in range(len(sentences))]
        left = self.embedder.embed(windows[:-1])
        right = self.embedder.embed(ahead[1:])
        sims = np.sum(left * right, axis=1)  # similarity across each gap
        threshold = float(np.percentile(sims, self.breakpoint_percentile))

        groups, current, size = [], [units[0]], count_tokens(sentences[0])
        for gap, unit in enumerate(units[1:]):
            n = count_tokens(unit[0])
            topic_shift = sims[gap] <= threshold and size >= self.min_size
            if current and (topic_shift or size + n > self.max_size):
                groups.append(current)
                current, size = [], 0
            current.append(unit)
            size += n
        if current:
            groups.append(current)
        return groups

    def chunk(self, sections: list[Section]) -> list[Chunk]:
        pieces: list[Chunk] = []
        for s in sections:
            if not s.text.strip():
                continue
            # (sentence, page) units; over-long sentences are cut at max_size words
            units: list[tuple[str, int | None]] = []
            for b in s.blocks:
                for sent in split_sentences(b.text):
                    parts = _split_long_sentence(sent, self.max_size) if count_tokens(sent) > self.max_size else [sent]
                    units.extend((p, b.page) for p in parts)
            if sum(count_tokens(u[0]) for u in units) <= self.max_size:
                groups = [units]
            else:
                groups = self._semantic_split(units)
            for group in groups:
                pieces.append(Chunk(text=" ".join(u[0] for u in group), section=s.title,
                                    strategy="dynamic", page=group[0][1]))

        # Merge undersized fragments - but only within the same section, and never past max_size.
        # A short section (e.g. "Fees: Annual fee is 75 dinars.") stays its own chunk under its own
        # heading rather than being absorbed by the next section. The one exception is untitled
        # preamble text (a document title line), which is glued to the start of the first section.
        merged: list[Chunk] = []
        carry: Chunk | None = None
        for c in pieces:
            if carry is not None:
                if c.token_count + carry.token_count <= self.max_size:
                    c.text = f"{carry.text} {c.text}"
                    c.page = carry.page if carry.page is not None else c.page
                else:
                    merged.append(carry)
                carry = None
            if c.token_count < self.min_size:
                if (
                    merged
                    and merged[-1].section == c.section
                    and merged[-1].token_count + c.token_count <= self.max_size
                ):
                    merged[-1].text += " " + c.text
                    continue
                if not c.section and c is not pieces[-1] and c.token_count < self.min_size // 2:
                    carry = c  # untitled preamble: prepend to the next chunk
                    continue
            merged.append(c)
        if carry is not None:
            merged.append(carry)
        for i, c in enumerate(merged):
            c.index = i
        return merged
