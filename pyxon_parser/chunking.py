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
    def _semantic_split(self, sentences: list[str]) -> list[list[str]]:
        if len(sentences) < 3:
            return [sentences]
        w = self.window
        windows = [" ".join(sentences[max(0, i - w + 1) : i + 1]) for i in range(len(sentences))]
        ahead = [" ".join(sentences[i : i + w]) for i in range(len(sentences))]
        left = self.embedder.embed(windows[:-1])
        right = self.embedder.embed(ahead[1:])
        sims = np.sum(left * right, axis=1)  # similarity across each gap
        threshold = float(np.percentile(sims, self.breakpoint_percentile))

        groups, current, size = [], [sentences[0]], count_tokens(sentences[0])
        for gap, sent in enumerate(sentences[1:]):
            n = count_tokens(sent)
            topic_shift = sims[gap] <= threshold and size >= self.min_size
            if current and (topic_shift or size + n > self.max_size):
                groups.append(current)
                current, size = [], 0
            current.append(sent)
            size += n
        if current:
            groups.append(current)
        return groups

    def chunk(self, sections: list[Section]) -> list[Chunk]:
        pieces: list[Chunk] = []
        for s in sections:
            page = s.blocks[0].page if s.blocks else None
            body = s.text
            if not body.strip():
                continue
            if count_tokens(body) <= self.max_size:
                pieces.append(Chunk(text=" ".join(b.text for b in s.blocks), section=s.title, strategy="dynamic", page=page))
                continue
            sentences = []
            for b in s.blocks:
                for sent in split_sentences(b.text):
                    if count_tokens(sent) > self.max_size:
                        sentences.extend(_split_long_sentence(sent, self.max_size))
                    else:
                        sentences.append(sent)
            for group in self._semantic_split(sentences):
                pieces.append(Chunk(text=" ".join(group), section=s.title, strategy="dynamic", page=page))

        # merge undersized fragments into the previous chunk of the same section
        merged: list[Chunk] = []
        carry = ""  # tiny fragment with no same-section predecessor (e.g. a title line)
        for c in pieces:
            if carry:
                c.text = f"{carry} {c.text}"
                carry = ""
            if c.token_count < self.min_size:
                if (
                    merged
                    and merged[-1].section == c.section
                    and merged[-1].token_count + c.token_count <= self.max_size * 1.25
                ):
                    merged[-1].text += " " + c.text
                    continue
                if c.token_count < self.min_size // 4 and c is not pieces[-1]:
                    carry = c.text  # glue it to the start of the next chunk
                    continue
            merged.append(c)
        if carry:
            merged.append(Chunk(text=carry, strategy="dynamic"))
        for i, c in enumerate(merged):
            c.index = i
        return merged
