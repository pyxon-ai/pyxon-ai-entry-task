"""End-to-end document processor: load -> analyze -> chunk -> embed -> store."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .analyzer import DocumentAnalysis, analyze
from .chunking import Chunk, DynamicChunker, FixedChunker
from .embeddings import Embedder, get_embedder
from .graph import build_graph
from .llm import get_llm
from .loaders import load_document
from .rag import RAGPipeline
from .raptor import build_tree
from .retrieval import HybridRetriever
from .storage import SQLStore, VectorStore
from .text import content_tokens


@dataclass
class IngestResult:
    document_id: int
    filename: str
    analysis: DocumentAnalysis
    chunks: list[Chunk]
    summaries: list[Chunk]
    timings: dict[str, float] = field(default_factory=dict)
    duplicate: bool = False


class PyxonParser:
    """Facade used by the demo, the benchmark and the tests.

    >>> parser = PyxonParser(data_dir="data")          # persistent
    >>> result = parser.ingest("samples/arabic_book.docx")
    >>> parser.search("ما هي فوائد الماء؟")
    >>> parser.ask("Which chunking strategy was used?")
    """

    def __init__(
        self,
        data_dir: str | Path | None = None,
        embedder: Embedder | None = None,
        fixed_chunk_size: int = 120,
        fixed_overlap: int = 20,
        dynamic_min: int = 40,
        dynamic_max: int = 220,
        build_raptor: bool = True,
        use_llm_summaries: bool = False,
    ):
        self.embedder = embedder or get_embedder()
        if data_dir is None:
            self.sql = SQLStore(":memory:")
            self.vectors = VectorStore(None, collection=f"pyxon_{id(self)}")
        else:
            data_dir = Path(data_dir)
            data_dir.mkdir(parents=True, exist_ok=True)
            self.sql = SQLStore(data_dir / "pyxon.sqlite3")
            self.vectors = VectorStore(data_dir / "chroma")
        self.fixed = FixedChunker(fixed_chunk_size, fixed_overlap)
        self.dynamic = DynamicChunker(self.embedder, dynamic_min, dynamic_max)
        self.build_raptor = build_raptor
        llm = get_llm() if use_llm_summaries else None
        self._summarize = (
            (lambda t: llm.complete("Summarize the passage in 2-3 sentences in its own language.", t[:6000], 250))
            if llm else None
        )
        self.retriever = HybridRetriever(self.sql, self.vectors, self.embedder)
        self.rag = RAGPipeline(self.retriever, self.sql)

    # -----------------------------------------------------------------------
    def chunk_document(self, path: str | Path, strategy: str = "auto"):
        """Load + analyze + chunk without storing (used by benchmarks)."""
        parsed = load_document(path)
        analysis, sections = analyze(parsed)
        chosen = analysis.strategy if strategy == "auto" else strategy
        chunker = self.dynamic if chosen == "dynamic" else self.fixed
        return parsed, analysis, sections, chunker.chunk(sections)

    def ingest(self, path: str | Path, strategy: str = "auto", replace: bool = True) -> IngestResult:
        t = {}
        t0 = time.perf_counter()
        parsed = load_document(path)
        t["load"] = time.perf_counter() - t0

        existing = self.sql.find_document(parsed.sha256)
        if existing is not None:
            if not replace:
                analysis, _ = analyze(parsed)
                return IngestResult(existing, parsed.filename, analysis, [], [], t, duplicate=True)
            self.delete(existing)

        t0 = time.perf_counter()
        analysis, sections = analyze(parsed)
        if strategy != "auto":
            analysis.reasons.insert(0, f"strategy forced to '{strategy}' by caller")
            analysis.strategy = strategy
        t["analyze"] = time.perf_counter() - t0

        t0 = time.perf_counter()
        chunker = self.dynamic if analysis.strategy == "dynamic" else self.fixed
        chunks = chunker.chunk(sections)
        t["chunk"] = time.perf_counter() - t0

        t0 = time.perf_counter()
        leaf_vecs = self.embedder.embed([c.embedding_text() for c in chunks]) if chunks else np.zeros((0, 1))
        t["embed"] = time.perf_counter() - t0

        t0 = time.perf_counter()
        summaries, sum_vecs = ([], None)
        if self.build_raptor and len(chunks) > 1:
            summaries, sum_vecs = build_tree(chunks, leaf_vecs, self.embedder, self._summarize)
        t["raptor"] = time.perf_counter() - t0

        t0 = time.perf_counter()
        doc_id = self.sql.insert_document(parsed, analysis, self.embedder.name)
        self.sql.insert_sections(doc_id, sections)
        all_nodes = chunks + summaries
        ids = [f"d{doc_id}-L{c.level}-{c.index}" for c in all_nodes]
        self.sql.insert_chunks(doc_id, [
            {
                "id": cid, "document_id": doc_id, "chunk_index": c.index, "level": c.level,
                "section": c.section, "page": c.page, "strategy": c.strategy, "text": c.text,
                "normalized_text": c.normalized, "token_count": c.token_count, "char_count": len(c.text),
                "children": ",".join(map(str, c.children)),
                "fts_tokens": " ".join(content_tokens(c.embedding_text())),
            }
            for cid, c in zip(ids, all_nodes)
        ])
        leaf_ids = ids[: len(chunks)]
        terms, edges = build_graph(leaf_ids, [c.embedding_text() for c in chunks])
        self.sql.insert_graph(doc_id, terms, edges)
        if all_nodes:
            vecs = leaf_vecs if not summaries else np.vstack([leaf_vecs, sum_vecs])
            self.vectors.add(
                ids, vecs, [c.text for c in all_nodes],
                [{"document_id": doc_id, "level": c.level, "section": c.section[:200], "strategy": c.strategy,
                  "language": analysis.language, "filename": parsed.filename} for c in all_nodes],
            )
        t["store"] = time.perf_counter() - t0
        t["total"] = sum(t.values())
        return IngestResult(doc_id, parsed.filename, analysis, chunks, summaries,
                            {k: round(v, 4) for k, v in t.items()})

    def delete(self, doc_id: int) -> None:
        self.vectors.delete_document(doc_id)
        self.sql.delete_document(doc_id)

    def search(self, query: str, k: int = 5, mode: str = "hybrid", **kw):
        return self.retriever.search(query, k=k, mode=mode, **kw)

    def ask(self, question: str, k: int = 5, **kw):
        return self.rag.ask(question, k=k, **kw)
