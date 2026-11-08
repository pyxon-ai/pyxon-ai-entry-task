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
from .loaders import EmptyDocumentError, load_document
from .rag import RAGPipeline
from .raptor import build_tree
from .retrieval import HybridRetriever
from .storage import SQLStore, VectorStore
from .text import LEXICAL_VERSION, content_tokens


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
            # in-memory: both stores are private to this parser (UUID collection)
            self.sql = SQLStore(":memory:")
            self.vectors = VectorStore(None, self.embedder.name, self.embedder.dim)
        else:
            data_dir = Path(data_dir)
            data_dir.mkdir(parents=True, exist_ok=True)
            self.sql = SQLStore(data_dir / "pyxon.sqlite3")
            # keyword index and term graph built with an older tokenizer: rebuild them from the
            # stored chunk texts (re-uploading an unchanged file is skipped, so it would never refresh)
            if self.sql.lexical_version() != LEXICAL_VERSION:
                if self.sql.chunk_count():
                    self.sql.rebuild_lexical(LEXICAL_VERSION, content_tokens, build_graph)
                else:
                    self.sql.set_lexical_version(LEXICAL_VERSION)
            # one collection per embedding model; if this model has no (or partial) vectors yet,
            # rebuild them from the chunk texts kept in SQLite instead of failing at query time
            self.vectors = VectorStore(data_dir / "chroma", self.embedder.name, self.embedder.dim)
            if self.vectors.count() != self.sql.chunk_count():
                self.reindex()
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
        if existing is not None and not replace:
            analysis, _ = analyze(parsed)
            return IngestResult(existing, parsed.filename, analysis, [], [], t, duplicate=True)

        t0 = time.perf_counter()
        analysis, sections = analyze(parsed)
        if strategy != "auto":
            analysis.reasons.insert(0, f"strategy forced to '{strategy}' by caller")
            analysis.strategy = strategy
        t["analyze"] = time.perf_counter() - t0

        t0 = time.perf_counter()
        chunker = self.dynamic if analysis.strategy == "dynamic" else self.fixed
        chunks = chunker.chunk(sections)
        if not chunks:
            raise EmptyDocumentError(
                f"{parsed.filename} has no indexable body text (only headings or empty sections)."
            )
        t["chunk"] = time.perf_counter() - t0

        # Everything that can fail slowly (embedding, summaries) happens before any write.
        t0 = time.perf_counter()
        leaf_vecs = self.embedder.embed([c.embedding_text() for c in chunks])
        t["embed"] = time.perf_counter() - t0

        t0 = time.perf_counter()
        summaries, sum_vecs = ([], None)
        if self.build_raptor and len(chunks) > 1:
            summaries, sum_vecs = build_tree(chunks, leaf_vecs, self.embedder, self._summarize)
        t["raptor"] = time.perf_counter() - t0

        # Writes: SQL in one transaction, committed only after the vectors are stored.
        # A failure rolls SQL back and removes any partially written vectors; when replacing,
        # the previous version stays intact until the new one is fully written.
        t0 = time.perf_counter()
        all_nodes = chunks + summaries
        ids: list[str] = []
        try:
            with self.sql.transaction():
                if existing is not None:
                    self.sql.delete_document(existing)  # uncommitted until the end of the block
                doc_id = self.sql.insert_document(parsed, analysis, self.embedder.name)
                self.sql.insert_sections(doc_id, sections)
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
                vecs = leaf_vecs if not summaries else np.vstack([leaf_vecs, sum_vecs])
                self.vectors.add(
                    ids, vecs, [c.text for c in all_nodes],
                    [{"document_id": doc_id, "level": c.level, "section": c.section[:200], "strategy": c.strategy,
                      "language": analysis.language, "filename": parsed.filename} for c in all_nodes],
                )
        except BaseException:
            try:
                self.vectors.delete_ids(ids)  # compensate a partial vector write
            except Exception:
                pass
            raise
        if existing is not None:
            self.vectors.delete_document(existing)  # old version removed only after success
        t["store"] = time.perf_counter() - t0
        t["total"] = sum(t.values())
        return IngestResult(doc_id, parsed.filename, analysis, chunks, summaries,
                            {k: round(v, 4) for k, v in t.items()})

    def reindex(self, batch: int = 256) -> int:
        """(Re)build the vector index for the current embedding model from the chunk texts in SQLite.

        Used automatically when a persistent store is opened with a model that has no vectors yet
        (e.g. switching PYXON_EMBEDDER from hashing to fastembed). Returns the number of vectors.
        """
        try:
            self.vectors.client.delete_collection(self.vectors.collection.name)
        except Exception:
            pass
        meta = {"hnsw:space": "cosine", "embedder": self.embedder.name, "dim": int(self.embedder.dim)}
        self.vectors.collection = self.vectors.client.get_or_create_collection(
            name=self.vectors.collection.name, metadata=meta, embedding_function=None
        )
        n = 0
        for ids, emb_texts, texts, metas in self.sql.all_chunks_for_index(batch):
            self.vectors.add(ids, self.embedder.embed(emb_texts), texts, metas)
            n += len(ids)
        return n

    def close(self) -> None:
        """Release the stores; an in-memory parser also drops its private vector collection."""
        self.vectors.close()
        self.sql.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def delete(self, doc_id: int) -> None:
        self.vectors.delete_document(doc_id)
        self.sql.delete_document(doc_id)

    def search(self, query: str, k: int = 5, mode: str = "hybrid", **kw):
        return self.retriever.search(query, k=k, mode=mode, **kw)

    def ask(self, question: str, k: int = 5, **kw):
        return self.rag.ask(question, k=k, **kw)
