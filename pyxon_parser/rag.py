"""RAG layer: retrieval -> grounded prompt -> LLM answer (or extractive fallback).

Also routes *structured* questions (how many documents, which files are in
Arabic, which strategy was used...) to the SQL database instead of the
vector store - the "uses the SQL database for structured queries" part of
the brief.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .arabic import detect_language, normalize_for_index
from . import query_router
from .llm import LLM, get_llm
from .retrieval import HybridRetriever, SearchResult
from .storage import SQLStore
from .text import content_tokens, split_sentences

SYSTEM_PROMPT = (
    "You answer questions using ONLY the provided context passages. "
    "Cite passages as [1], [2]... If the answer is not in the context, say you don't know. "
    "Answer in the same language as the question; when quoting Arabic keep the original diacritics."
)

@dataclass
class Answer:
    question: str
    answer: str
    route: str  # 'rag' | 'sql'
    contexts: list[SearchResult] = field(default_factory=list)
    sql: str | None = None
    params: list = field(default_factory=list)
    rows: list[dict] = field(default_factory=list)
    llm_used: bool = False


def build_prompt(question: str, contexts: list[SearchResult]) -> str:
    parts = []
    for i, c in enumerate(contexts, start=1):
        where = f"{c.filename}" + (f" — {c.section}" if c.section else "") + (f" (p.{c.page})" if c.page else "")
        parts.append(f"[{i}] ({where})\n{c.text}")
    return "Context passages:\n\n" + "\n\n".join(parts) + f"\n\nQuestion: {question}\nAnswer:"


def extractive_answer(
    question: str,
    contexts: list[SearchResult],
    max_sentences: int = 3,
    min_score: float = 0.34,
    relative: float = 0.6,
) -> str:
    """No-LLM fallback: quote the context sentences that best cover the question.

    Each question word is weighted by how rare it is among the candidate sentences, so a
    sentence matching only a common word (e.g. a staff record that happens to contain the
    name "نور") cannot ride along with the real answer. A sentence is quoted only if its
    weighted coverage is at least ``min_score`` and at least ``relative`` x the best one;
    if nothing reaches ``min_score`` the answer is "not found" instead of a guess.
    """
    q = set(content_tokens(question))
    candidates, seen = [], set()
    for ci, c in enumerate(contexts, start=1):
        for si, s in enumerate(split_sentences(c.text)):
            key = normalize_for_index(s)
            toks = set(content_tokens(s))
            if toks and key not in seen:  # skip the same sentence from another copy of a document
                seen.add(key)
                candidates.append((ci, si, s, toks))
    df = {t: sum(t in toks for *_, toks in candidates) for t in q}
    weights = {t: 1.0 / df[t] for t in q if df[t]}  # query words absent everywhere carry no signal
    total = sum(weights.values())
    scored = []
    if total:
        for ci, si, s, toks in candidates:
            score = sum(w for t, w in weights.items() if t in toks) / total
            scored.append((score, -ci, -si, s, ci))
    scored.sort(reverse=True)
    if not scored or scored[0][0] < min_score:
        return "I could not find this in the indexed documents." if detect_language(question) != "ar" \
            else "لم أجد إجابة في المستندات المفهرسة."
    cutoff = max(min_score, relative * scored[0][0])
    best = [x for x in scored[:max_sentences] if x[0] >= cutoff]
    return " ".join(f"{s} [{ci}]" for *_, s, ci in best)


class RAGPipeline:
    def __init__(self, retriever: HybridRetriever, sql: SQLStore, llm: LLM | None = None):
        self.retriever, self.sql = retriever, sql
        self.llm = llm if llm is not None else get_llm()

    def route(self, question: str, doc_ids: list[int] | None = None):
        """A parameterised SELECT for corpus-metadata questions, or None for content questions."""
        return query_router.parse(question, doc_ids)

    def ask(self, question: str, k: int = 5, doc_ids: list[int] | None = None) -> Answer:
        sq = self.route(question, doc_ids)
        if sq is not None:
            rows = self.sql.run_readonly_query(sq.sql, params=sq.params)
            if sq.kind == "count" and rows:
                (label, value), = rows[0].items()
                text = f"{value} {label}."
            else:
                text = f"{len(rows)} row(s) from the SQL database."
            return Answer(question, text, "sql", sql=sq.sql, params=list(sq.params), rows=rows)

        contexts = self.retriever.search(question, k=k, include_summaries=True, doc_ids=doc_ids)
        if self.llm and contexts:
            try:
                text = self.llm.complete(SYSTEM_PROMPT, build_prompt(question, contexts))
                return Answer(question, text, "rag", contexts, llm_used=True)
            except Exception as exc:  # network/key problems -> degrade gracefully
                fallback = extractive_answer(question, contexts)
                return Answer(question, f"{fallback}\n\n(LLM call failed: {exc})", "rag", contexts)
        return Answer(question, extractive_answer(question, contexts), "rag", contexts)
