import json
import sqlite3
import threading
from typing import Any, Iterable

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm


class SqlStore:
    def __init__(self, path: str):
        self.path = path
        self._init()

    def _conn(self):
        con = sqlite3.connect(self.path, check_same_thread=False, timeout=30)
        try:
            con.execute("PRAGMA journal_mode=WAL")
            con.execute("PRAGMA synchronous=NORMAL")
            con.execute("PRAGMA temp_store=MEMORY")
        except Exception:
            pass
        return con

    def _init(self):
        con = self._conn()
        cur = con.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS documents(
            doc_id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            file_type TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            strategy TEXT NOT NULL,
            metrics_json TEXT NOT NULL,
            n_pages INTEGER NOT NULL,
            n_chunks INTEGER NOT NULL
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS chunks(
            chunk_id TEXT PRIMARY KEY,
            doc_id TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            page_start INTEGER NOT NULL,
            page_end INTEGER NOT NULL,
            section_path TEXT NOT NULL,
            char_start INTEGER NOT NULL,
            char_end INTEGER NOT NULL,
            text_raw TEXT NOT NULL,
            text_kw TEXT NOT NULL,
            lang_json TEXT NOT NULL
        )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(doc_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_chunks_doc_idx ON chunks(doc_id, chunk_index)")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS benchmark_cases(
            case_id TEXT PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            doc_id TEXT NOT NULL,
            query TEXT NOT NULL,
            gold_json TEXT NOT NULL,
            notes TEXT NOT NULL,
            k_suggest INTEGER DEFAULT 5
        )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_bench_doc ON benchmark_cases(doc_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_bench_created ON benchmark_cases(created_at)")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS benchmark_runs(
            run_id TEXT PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            config_json TEXT NOT NULL,
            metrics_json TEXT NOT NULL
        )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_runs_created ON benchmark_runs(created_at)")

        con.commit()
        con.close()

    def upsert_document(self, doc: dict[str, Any]):
        con = self._conn()
        cur = con.cursor()
        cur.execute("""
        INSERT INTO documents(doc_id, filename, file_type, strategy, metrics_json, n_pages, n_chunks)
        VALUES(?,?,?,?,?,?,?)
        ON CONFLICT(doc_id) DO UPDATE SET
            filename=excluded.filename,
            file_type=excluded.file_type,
            strategy=excluded.strategy,
            metrics_json=excluded.metrics_json,
            n_pages=excluded.n_pages,
            n_chunks=excluded.n_chunks
        """, (
            doc["doc_id"], doc["filename"], doc["file_type"], doc["strategy"],
            json.dumps(doc["metrics"], ensure_ascii=False),
            int(doc["n_pages"]), int(doc["n_chunks"])
        ))
        con.commit()
        con.close()

    def upsert_chunks(self, chunks: Iterable[dict[str, Any]]):
        con = self._conn()
        cur = con.cursor()
        cur.executemany("""
        INSERT INTO chunks(chunk_id, doc_id, chunk_index, page_start, page_end, section_path, char_start, char_end, text_raw, text_kw, lang_json)
        VALUES(?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(chunk_id) DO UPDATE SET
            doc_id=excluded.doc_id,
            chunk_index=excluded.chunk_index,
            page_start=excluded.page_start,
            page_end=excluded.page_end,
            section_path=excluded.section_path,
            char_start=excluded.char_start,
            char_end=excluded.char_end,
            text_raw=excluded.text_raw,
            text_kw=excluded.text_kw,
            lang_json=excluded.lang_json
        """, [(
            c["chunk_id"], c["doc_id"], int(c["chunk_index"]), int(c["page_start"]), int(c["page_end"]), c["section_path"],
            int(c["char_start"]), int(c["char_end"]), c["text_raw"], c["text_kw"], json.dumps(c["lang"], ensure_ascii=False)
        ) for c in chunks])
        con.commit()
        con.close()

    def list_documents(self, limit: int = 200) -> list[dict[str, Any]]:
        con = self._conn()
        cur = con.cursor()
        rows = cur.execute("""
        SELECT doc_id, filename, file_type, created_at, strategy, metrics_json, n_pages, n_chunks
        FROM documents ORDER BY created_at DESC LIMIT ?
        """, (int(limit),)).fetchall()
        con.close()
        out = []
        for r in rows:
            out.append({
                "doc_id": r[0], "filename": r[1], "file_type": r[2], "created_at": r[3],
                "strategy": r[4], "metrics": json.loads(r[5]), "n_pages": r[6], "n_chunks": r[7]
            })
        return out

    def list_chunks_by_doc(self, doc_id: str, limit: int = 1000) -> list[dict[str, Any]]:
        con = self._conn()
        cur = con.cursor()
        rows = cur.execute("""
        SELECT chunk_id, chunk_index, page_start, page_end, section_path, char_start, char_end, text_raw, text_kw, lang_json
        FROM chunks WHERE doc_id=? ORDER BY chunk_index ASC LIMIT ?
        """, (doc_id, int(limit))).fetchall()
        con.close()
        out = []
        for r in rows:
            out.append({
                "chunk_id": r[0], "chunk_index": r[1], "page_start": r[2], "page_end": r[3],
                "section_path": r[4], "char_start": r[5], "char_end": r[6],
                "text_raw": r[7], "text_kw": r[8], "lang": json.loads(r[9])
            })
        return out

    def get_chunks_by_doc(self, doc_id: str) -> list[dict[str, Any]]:
        return self.list_chunks_by_doc(doc_id, limit=1000000)

    def get_all_chunks_for_bm25(self) -> tuple[list[str], list[str]]:
        con = self._conn()
        cur = con.cursor()
        rows = cur.execute("SELECT chunk_id, text_kw FROM chunks").fetchall()
        con.close()
        ids = [r[0] for r in rows]
        texts = [r[1] for r in rows]
        return ids, texts

    def get_chunk_text(self, chunk_id: str) -> str | None:
        con = self._conn()
        cur = con.cursor()
        row = cur.execute("SELECT text_raw FROM chunks WHERE chunk_id=?", (chunk_id,)).fetchone()
        con.close()
        return row[0] if row else None

    def delete_document(self, doc_id: str):
        con = self._conn()
        cur = con.cursor()
        cur.execute("DELETE FROM benchmark_cases WHERE doc_id=?", (doc_id,))
        cur.execute("DELETE FROM chunks WHERE doc_id=?", (doc_id,))
        cur.execute("DELETE FROM documents WHERE doc_id=?", (doc_id,))
        con.commit()
        con.close()

    def upsert_benchmark_case(self, case: dict[str, Any]):
        con = self._conn()
        cur = con.cursor()
        cur.execute("""
        INSERT INTO benchmark_cases(case_id, doc_id, query, gold_json, notes, k_suggest)
        VALUES(?,?,?,?,?,?)
        ON CONFLICT(case_id) DO UPDATE SET
            doc_id=excluded.doc_id,
            query=excluded.query,
            gold_json=excluded.gold_json,
            notes=excluded.notes,
            k_suggest=excluded.k_suggest
        """, (
            case["case_id"],
            case["doc_id"],
            case["query"],
            json.dumps(case.get("gold") or [], ensure_ascii=False),
            case.get("notes") or "",
            int(case.get("k_suggest") or 5),
        ))
        con.commit()
        con.close()

    def add_benchmark_case(self, case_id: str, doc_id: str, query: str, gold: list[str], notes: str):
        self.upsert_benchmark_case({
            "case_id": case_id,
            "doc_id": doc_id,
            "query": query,
            "gold": gold,
            "notes": notes,
            "k_suggest": 5,
        })

    def list_benchmark_cases(self, limit: int = 500) -> list[dict[str, Any]]:
        con = self._conn()
        cur = con.cursor()
        rows = cur.execute("""
        SELECT case_id, created_at, doc_id, query, gold_json, notes, k_suggest
        FROM benchmark_cases ORDER BY created_at DESC LIMIT ?
        """, (int(limit),)).fetchall()
        con.close()
        out = []
        for r in rows:
            out.append({
                "case_id": r[0],
                "created_at": r[1],
                "doc_id": r[2],
                "query": r[3],
                "gold": json.loads(r[4]),
                "notes": r[5],
                "k_suggest": r[6],
            })
        return out

    def clear_benchmark_cases(self):
        con = self._conn()
        cur = con.cursor()
        cur.execute("DELETE FROM benchmark_cases")
        con.commit()
        con.close()

    def delete_benchmark_case(self, case_id: str):
        con = self._conn()
        cur = con.cursor()
        cur.execute("DELETE FROM benchmark_cases WHERE case_id=?", (case_id,))
        con.commit()
        con.close()

    def save_benchmark_run(self, run_id: str, config: dict[str, Any], metrics: dict[str, Any]):
        con = self._conn()
        cur = con.cursor()
        cur.execute("""
        INSERT INTO benchmark_runs(run_id, config_json, metrics_json)
        VALUES(?,?,?)
        """, (
            run_id,
            json.dumps(config, ensure_ascii=False),
            json.dumps(metrics, ensure_ascii=False),
        ))
        con.commit()
        con.close()

    def list_benchmark_runs(self, limit: int = 50) -> list[dict[str, Any]]:
        con = self._conn()
        cur = con.cursor()
        rows = cur.execute("""
        SELECT run_id, created_at, config_json, metrics_json
        FROM benchmark_runs ORDER BY created_at DESC LIMIT ?
        """, (int(limit),)).fetchall()
        con.close()
        out = []
        for r in rows:
            out.append({
                "run_id": r[0],
                "created_at": r[1],
                "config": json.loads(r[2]),
                "metrics": json.loads(r[3]),
            })
        return out


_QDRANT_LOCK = threading.Lock()
_QDRANT_CLIENTS: dict[str, QdrantClient] = {}


def _get_qdrant_client(path: str | None) -> QdrantClient:
    key = path or ":memory:"
    with _QDRANT_LOCK:
        cli = _QDRANT_CLIENTS.get(key)
        if cli is not None:
            return cli
        cli = QdrantClient(path=path) if path else QdrantClient(":memory:")
        _QDRANT_CLIENTS[key] = cli
        return cli


class VectorStore:
    def __init__(self, path: str | None):
        self.client = _get_qdrant_client(path)
        self.collection = "chunks"
        self._dim = None

    def ensure(self, dim: int):
        self._dim = int(dim)
        if self.client.collection_exists(self.collection):
            info = self.client.get_collection(self.collection)
            cur_dim = info.config.params.vectors.size
            if int(cur_dim) == int(dim):
                return
            self.client.delete_collection(self.collection)
        self.client.create_collection(
            collection_name=self.collection,
            vectors_config=qm.VectorParams(size=int(dim), distance=qm.Distance.COSINE)
        )

    def _ensure_if_missing(self):
        if self.client.collection_exists(self.collection):
            return
        if self._dim is None:
            raise ValueError("vector_collection_missing_dim")
        self.ensure(self._dim)

    def upsert(self, ids: list[str], vectors: list[list[float]], payloads: list[dict]):
        if self._dim is None and vectors:
            self.ensure(len(vectors[0]))
        else:
            self._ensure_if_missing()
        self.client.upsert(
            collection_name=self.collection,
            points=qm.Batch(ids=ids, vectors=vectors, payloads=payloads)
        )

    def search(self, vector: list[float], limit: int = 10):
        if not self.client.collection_exists(self.collection):
            self.ensure(len(vector))
        return self.client.search(
            collection_name=self.collection,
            query_vector=vector,
            limit=int(limit),
            with_payload=True
        )

    def delete_by_doc(self, doc_id: str):
        if not self.client.collection_exists(self.collection):
            return
        self.client.delete(
            collection_name=self.collection,
            points_selector=qm.FilterSelector(
                filter=qm.Filter(
                    must=[qm.FieldCondition(key="doc_id", match=qm.MatchValue(value=doc_id))]
                )
            )
        )
