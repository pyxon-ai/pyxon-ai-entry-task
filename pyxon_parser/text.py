"""Language-agnostic text helpers: sentence splitting, tokenizing, keywords."""
from __future__ import annotations

import math
import re
from collections import Counter

from .arabic import ARABIC_STOPWORDS, normalize_for_index

# Sentence ends: Latin . ! ? and Arabic question mark / full stop, followed by space.
# Split after . ! ? and Arabic ؟ ۔ — but not after a single-letter initial ("L. Nasser") or "e.g."/"i.e."
_SENT_SPLIT_RE = re.compile(r"(?<![\s(][A-Za-z]\.)(?<!^[A-Za-z]\.)(?<!\be\.g\.)(?<!\bi\.e\.)(?<=[.!?\u061F\u06D4])\s+")
# \w covers Arabic letters/digits; harakat (combining marks) are added so vocalized words stay whole.
_TOKEN_RE = re.compile(r"[\w\u064B-\u065F\u0670]+", re.UNICODE)

ENGLISH_STOPWORDS = set(
    """a an the and or but if then else of to in on at by for with from as is are was were be been
    being it its this that these those there here which who whom whose what when where why how all
    any both each few more most other some such no nor not only own same so than too very can will
    just should now also into about over after before between through during under again further
    once he she they them his her their we our you your i me my do does did doing have has had
    having would could may might must shall up down out off per via upon while within without""".split()
)
# Structural words ("chapter", "الفصل") say nothing about content.
STRUCTURAL = {"chapter", "section", "part", "فصل", "الفصل", "باب", "الباب", "قسم", "القسم"}
STOPWORDS = ENGLISH_STOPWORDS | ARABIC_STOPWORDS | STRUCTURAL


def split_sentences(text: str) -> list[str]:
    parts = _SENT_SPLIT_RE.split(text.strip())
    return [p.strip() for p in parts if p.strip()]


def tokenize(text: str) -> list[str]:
    """Normalized word tokens (diacritics stripped, lowercase)."""
    return _TOKEN_RE.findall(normalize_for_index(text))


def content_tokens(text: str) -> list[str]:
    out = []
    for t in tokenize(text):
        is_arabic = "\u0600" <= t[0] <= "\u06FF"
        if t in STOPWORDS or len(t) < (2 if is_arabic else 3) or t.isdigit():
            continue
        # Strip the Arabic definite article so "المياه" and "مياه" match.
        if t.startswith("ال") and len(t) > 4:
            t = t[2:]
        elif t.startswith(("وال", "بال", "فال", "كال")) and len(t) > 5:
            t = t[3:]
        out.append(t)
    return out


def count_tokens(text: str) -> int:
    """Cheap token count (words). Good enough for chunk sizing in both scripts."""
    return len(_TOKEN_RE.findall(text))


def top_keywords(text: str, k: int = 10, corpus_df: Counter | None = None, n_docs: int = 1) -> list[str]:
    """TF (or TF-IDF when document frequencies are supplied) keyword ranking."""
    tf = Counter(content_tokens(text))
    if not tf:
        return []
    if corpus_df:
        scored = {t: c * math.log((1 + n_docs) / (1 + corpus_df.get(t, 0))) for t, c in tf.items()}
    else:
        scored = dict(tf)
    return [t for t, _ in sorted(scored.items(), key=lambda x: (-x[1], x[0]))[:k]]
