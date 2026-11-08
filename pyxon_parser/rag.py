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
from .llm import LLM, get_llm
from .retrieval import HybridRetriever, SearchResult
from .storage import SQLStore
from .text import content_tokens, split_sentences

SYSTEM_PROMPT = (
    "You answer questions using ONLY the provided context passages. "
    "Cite passages as [1], [2]... If the answer is not in the context, say you don't know. "
    "Answer in the same language as the question; when quoting Arabic keep the original diacritics."
)

# Simple intent rules for structured (SQL) questions, English + Arabic.
_STRUCTURED_RULES = [
    (re.compile(r"how many (documents|files)|كم (عدد )?(الملفات|المستندات|الوثائق)", re.I),
     "SELECT COUNT(*) AS documents FROM documents"),
    (re.compile(r"(list|which|show).*(documents|files)|ما (هي )?(الملفات|المستندات)", re.I),
     "SELECT id, filename, file_type, language, strategy, doc_type FROM documents ORDER BY id"),
    (re.compile(r"arabic (documents|files)|(الملفات|المستندات) العربية", re.I),
     "SELECT id, filename, has_diacritics FROM documents WHERE language IN ('ar','mixed')"),
    (re.compile(r"(chunking )?strateg(y|ies)|استراتيجية", re.I),
     "SELECT filename, strategy, strategy_reasons FROM documents"),
    (re.compile(r"how many chunks|كم (عدد )?(المقاطع|الأجزاء)", re.I),
     "SELECT d.filename, COUNT(c.id) AS chunks FROM documents d JOIN chunks c ON c.document_id=d.id "
     "AND c.level=0 GROUP BY d.id"),
]


@dataclass
class Answer:
    question: str
    answer: str
    route: str  # 'rag' | 'sql'
    contexts: list[SearchResult] = field(default_factory=list)
    sql: str | None = None
    rows: list[dict] = field(default_factory=list)
    llm_used: bool = False


def build_prompt(question: str, contexts: list[SearchResult]) -> str:
    parts = []
    for i, c in enumerate(contexts, start=1):
        where = f"{c.filename}" + (f" — {c.section}" if c.section else "") + (f" (p.{c.page})" if c.page else "")
        parts.append(f"[{i}] ({where})\n{c.text}")
    return "Context passages:\n\n" + "\n\n".join(parts) + f"\n\nQuestion: {question}\nAnswer:"


def extractive_answer(question: str, contexts: list[SearchResult], max_sentences: int = 3) -> str:
    """No-LLM fallback: the context sentences that overlap most with the question."""
    q = set(content_tokens(question))
    scored, seen = [], set()
    for ci, c in enumerate(contexts, start=1):
        for si, s in enumerate(split_sentences(c.text)):
            toks = set(content_tokens(s))
            key = normalize_for_index(s)
            if toks and key not in seen:  # skip the same sentence from another copy of a document
                seen.add(key)
                overlap = len(q & toks) / (len(q) or 1)
                scored.append((overlap, -ci, -si, s, ci))
    best = [x for x in sorted(scored, reverse=True)[:max_sentences] if x[0] > 0]
    if not best:
        return "I could not find this in the indexed documents." if detect_language(question) != "ar" \
            else "لم أجد إجابة في المستندات المفهرسة."
    return " ".join(f"{s} [{ci}]" for *_, s, ci in best)


class RAGPipeline:
    def __init__(self, retriever: HybridRetriever, sql: SQLStore, llm: LLM | None = None):
        self.retriever, self.sql = retriever, sql
        self.llm = llm if llm is not None else get_llm()

    def route(self, question: str) -> str | None:
        for pattern, sql in _STRUCTURED_RULES:
            if pattern.search(question):
                return sql
        return None

    def ask(self, question: str, k: int = 5, doc_ids: list[int] | None = None) -> Answer:
        sql = self.route(question)
        if sql:
            rows = self.sql.run_readonly_query(sql)
            return Answer(question, f"{len(rows)} row(s) from the SQL database.", "sql", sql=sql, rows=rows)

        contexts = self.retriever.search(question, k=k, include_summaries=True, doc_ids=doc_ids)
        if self.llm and contexts:
            try:
                text = self.llm.complete(SYSTEM_PROMPT, build_prompt(question, contexts))
                return Answer(question, text, "rag", contexts, llm_used=True)
            except Exception as exc:  # network/key problems -> degrade gracefully
                fallback = extractive_answer(question, contexts)
                return Answer(question, f"{fallback}\n\n(LLM call failed: {exc})", "rag", contexts)
        return Answer(question, extractive_answer(question, contexts), "rag", contexts)
