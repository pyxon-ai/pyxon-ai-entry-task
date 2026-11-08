"""Persistence: SQLite for metadata/structure/keywords, Chroma for vectors.

SQL schema (see ``SCHEMA``):

* ``documents``  - one row per file: type, language, diacritics, strategy and why
* ``sections``   - detected headings in reading order
* ``chunks``     - every chunk (leaf and RAPTOR summary) with original text
* ``chunks_fts`` - FTS5 index over normalized, light-stemmed tokens (BM25 keyword search)
* ``terms`` / ``term_edges`` - the per-document knowledge graph (concept co-occurrence)

The vector store holds the same chunk ids, so results from either side can be
joined back to full rows with :meth:`SQLStore.get_chunks`.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import threading
from pathlib import Path

import numpy as np

# chromadb's bundled posthog client is noisy (and telemetry is disabled anyway)
logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL,
    sha256 TEXT UNIQUE NOT NULL,
    language TEXT,
    direction TEXT,
    has_diacritics INTEGER,
    diacritic_density REAL,
    num_pages INTEGER,
    num_tokens INTEGER,
    doc_type TEXT,
    strategy TEXT,
    strategy_reasons TEXT,
    keywords TEXT,
    summary TEXT,
    meta TEXT,
    embedder TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS sections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    title TEXT,
    level INTEGER
);
CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    level INTEGER NOT NULL DEFAULT 0,
    section TEXT,
    page INTEGER,
    strategy TEXT,
    text TEXT NOT NULL,
    normalized_text TEXT NOT NULL,
    token_count INTEGER,
    char_count INTEGER,
    children TEXT
);
CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(document_id, level);
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(chunk_id UNINDEXED, document_id UNINDEXED, level UNINDEXED, tokens);
CREATE TABLE IF NOT EXISTS terms (
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    term TEXT NOT NULL,
    frequency INTEGER,
    centrality REAL,
    chunk_ids TEXT,
    PRIMARY KEY (document_id, term)
);
CREATE TABLE IF NOT EXISTS term_edges (
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    source TEXT NOT NULL,
    target TEXT NOT NULL,
    weight REAL,
    PRIMARY KEY (document_id, source, target)
);
"""


class SQLStore:
    def __init__(self, path: str | Path = ":memory:"):
        self.path = str(path)
        self._lock = threading.RLock()
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)

    # -- writes --------------------------------------------------------------
    def find_document(self, sha256: str) -> int | None:
        row = self.conn.execute("SELECT id FROM documents WHERE sha256 = ?", (sha256,)).fetchone()
        return row["id"] if row else None

    def insert_document(self, parsed, analysis, embedder_name: str) -> int:
        with self._lock, self.conn:
            cur = self.conn.execute(
                """INSERT INTO documents (filename, file_type, sha256, language, direction, has_diacritics,
                   diacritic_density, num_pages, num_tokens, doc_type, strategy, strategy_reasons, keywords,
                   summary, meta, embedder) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    parsed.filename, parsed.file_type, parsed.sha256, analysis.language, analysis.direction,
                    int(analysis.has_diacritics), analysis.diacritic_density, parsed.num_pages,
                    analysis.num_tokens, analysis.doc_type, analysis.strategy,
                    json.dumps(analysis.reasons, ensure_ascii=False),
                    json.dumps(analysis.keywords, ensure_ascii=False), analysis.summary,
                    json.dumps(parsed.meta, ensure_ascii=False, default=str), embedder_name,
                ),
            )
            return cur.lastrowid

    def insert_sections(self, doc_id: int, sections) -> None:
        with self._lock, self.conn:
            self.conn.executemany(
                "INSERT INTO sections (document_id, position, title, level) VALUES (?,?,?,?)",
                [(doc_id, i, s.title, s.level) for i, s in enumerate(sections) if s.title],
            )

    def insert_chunks(self, doc_id: int, rows: list[dict]) -> None:
        with self._lock, self.conn:
            self.conn.executemany(
                """INSERT INTO chunks (id, document_id, chunk_index, level, section, page, strategy, text,
                   normalized_text, token_count, char_count, children) VALUES
                   (:id,:document_id,:chunk_index,:level,:section,:page,:strategy,:text,:normalized_text,
                    :token_count,:char_count,:children)""",
                rows,
            )
            self.conn.executemany(
                "INSERT INTO chunks_fts (chunk_id, document_id, level, tokens) VALUES (?,?,?,?)",
                [(r["id"], doc_id, r["level"], r["fts_tokens"]) for r in rows],
            )

    def insert_graph(self, doc_id: int, terms: list[dict], edges: list[tuple[str, str, float]]) -> None:
        with self._lock, self.conn:
            self.conn.executemany(
                "INSERT INTO terms (document_id, term, frequency, centrality, chunk_ids) VALUES (?,?,?,?,?)",
                [(doc_id, t["term"], t["frequency"], t["centrality"], json.dumps(t["chunk_ids"])) for t in terms],
            )
            self.conn.executemany(
                "INSERT INTO term_edges (document_id, source, target, weight) VALUES (?,?,?,?)",
                [(doc_id, a, b, w) for a, b, w in edges],
            )

    def delete_document(self, doc_id: int) -> None:
        with self._lock, self.conn:
            self.conn.execute("DELETE FROM chunks_fts WHERE document_id = ?", (doc_id,))
            self.conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))

    # -- reads ---------------------------------------------------------------
    def list_documents(self) -> list[dict]:
        rows = self.conn.execute(
            """SELECT d.id, d.filename, d.file_type, d.language, d.has_diacritics, d.doc_type, d.strategy,
                      d.num_tokens, COUNT(c.id) AS chunks
               FROM documents d LEFT JOIN chunks c ON c.document_id = d.id AND c.level = 0
               GROUP BY d.id ORDER BY d.id"""
        ).fetchall()
        return [dict(r) for r in rows]

    def get_document(self, doc_id: int) -> dict | None:
        row = self.conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        for key in ("strategy_reasons", "keywords", "meta"):
            d[key] = json.loads(d[key]) if d[key] else None
        return d

    def get_chunks(self, ids: list[str]) -> dict[str, dict]:
        if not ids:
            return {}
        q = ",".join("?" * len(ids))
        rows = self.conn.execute(
            f"""SELECT c.*, d.filename FROM chunks c JOIN documents d ON d.id = c.document_id
                WHERE c.id IN ({q})""",
            ids,
        ).fetchall()
        return {r["id"]: dict(r) for r in rows}

    def document_chunks(self, doc_id: int, level: int | None = 0) -> list[dict]:
        sql = "SELECT * FROM chunks WHERE document_id = ?"
        args: list = [doc_id]
        if level is not None:
            sql += " AND level = ?"
            args.append(level)
        return [dict(r) for r in self.conn.execute(sql + " ORDER BY level, chunk_index", args)]

    def keyword_search(self, tokens: list[str], k: int = 10, level: int | None = 0, doc_ids=None) -> list[tuple[str, float]]:
        """BM25 over FTS5. Returns (chunk_id, score) with higher = better."""
        tokens = [t.replace('"', "") for t in tokens if t]
        if not tokens:
            return []
        match = " OR ".join(f'"{t}"' for t in dict.fromkeys(tokens))
        sql = "SELECT chunk_id, bm25(chunks_fts) AS s FROM chunks_fts WHERE chunks_fts MATCH ?"
        args: list = [match]
        if level is not None:
            sql += " AND level = ?"
            args.append(level)
        if doc_ids:
            sql += f" AND document_id IN ({','.join('?' * len(doc_ids))})"
            args.extend(doc_ids)
        sql += " ORDER BY s LIMIT ?"
        args.append(k)
        return [(r["chunk_id"], -r["s"]) for r in self.conn.execute(sql, args)]

    def terms_for(self, tokens: list[str], doc_ids=None) -> list[dict]:
        if not tokens:
            return []
        sql = f"SELECT * FROM terms WHERE term IN ({','.join('?' * len(tokens))})"
        args = list(tokens)
        if doc_ids:
            sql += f" AND document_id IN ({','.join('?' * len(doc_ids))})"
            args.extend(doc_ids)
        return [dict(r) for r in self.conn.execute(sql, args)]

    def neighbors(self, doc_id: int, term: str, k: int = 5) -> list[dict]:
        rows = self.conn.execute(
            """SELECT CASE WHEN source = ? THEN target ELSE source END AS term, weight
               FROM term_edges WHERE document_id = ? AND (source = ? OR target = ?)
               ORDER BY weight DESC LIMIT ?""",
            (term, doc_id, term, term, k),
        ).fetchall()
        return [dict(r) for r in rows]

    def top_terms(self, doc_id: int, k: int = 15) -> list[dict]:
        rows = self.conn.execute(
            "SELECT term, frequency, centrality FROM terms WHERE document_id = ? ORDER BY centrality DESC LIMIT ?",
            (doc_id, k),
        ).fetchall()
        return [dict(r) for r in rows]

    def run_readonly_query(self, sql: str, limit: int = 200) -> list[dict]:
        """Structured-query entry point for the RAG layer / demo. SELECT statements only."""
        stripped = sql.strip().rstrip(";")
        if not stripped.lower().startswith(("select", "with")) or ";" in stripped:
            raise ValueError("Only a single read-only SELECT statement is allowed")
        ro = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True) if self.path != ":memory:" else self.conn
        ro.row_factory = sqlite3.Row
        rows = ro.execute(stripped).fetchmany(limit)
        return [dict(r) for r in rows]

    def stats(self) -> dict:
        one = lambda q: self.conn.execute(q).fetchone()[0]  # noqa: E731
        return {
            "documents": one("SELECT COUNT(*) FROM documents"),
            "leaf_chunks": one("SELECT COUNT(*) FROM chunks WHERE level = 0"),
            "summary_nodes": one("SELECT COUNT(*) FROM chunks WHERE level > 0"),
            "terms": one("SELECT COUNT(*) FROM terms"),
            "edges": one("SELECT COUNT(*) FROM term_edges"),
        }


class VectorStore:
    """Thin wrapper over a Chroma collection (cosine space, external embeddings)."""

    def __init__(self, path: str | Path | None = None, collection: str = "pyxon_chunks"):
        import chromadb
        from chromadb.config import Settings

        settings = Settings(anonymized_telemetry=False, allow_reset=True)
        if path is None:
            self.client = chromadb.EphemeralClient(settings=settings)
        else:
            self.client = chromadb.PersistentClient(path=str(path), settings=settings)
        self.collection = self.client.get_or_create_collection(
            name=collection, metadata={"hnsw:space": "cosine"}, embedding_function=None
        )

    def add(self, ids: list[str], vectors: np.ndarray, documents: list[str], metadatas: list[dict]) -> None:
        for start in range(0, len(ids), 1000):
            end = start + 1000
            self.collection.add(
                ids=ids[start:end],
                embeddings=vectors[start:end].tolist(),
                documents=documents[start:end],
                metadatas=metadatas[start:end],
            )

    def query(self, vector: np.ndarray, k: int = 10, where: dict | None = None) -> list[tuple[str, float]]:
        n = self.collection.count()
        if n == 0:
            return []
        res = self.collection.query(
            query_embeddings=[vector.tolist()], n_results=min(k, n), where=where or None, include=["distances"]
        )
        return [(i, 1.0 - d) for i, d in zip(res["ids"][0], res["distances"][0])]

    def delete_document(self, doc_id: int) -> None:
        self.collection.delete(where={"document_id": doc_id})

    def count(self) -> int:
        return self.collection.count()
