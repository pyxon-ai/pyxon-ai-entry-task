"""
SQLite store for documents and chunks metadata. Relational queries.
"""

import json
import os
import sqlite3
from pathlib import Path
from typing import Any


def _default_db_path() -> str:
    return os.environ.get("SQLITE_PATH", "./data/documents.db")


class SQLStore:
    """SQLite-backed store: documents table, chunks table."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or _default_db_path()
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_schema(self) -> None:
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    path TEXT,
                    format TEXT,
                    strategy TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    char_start INTEGER,
                    char_end INTEGER,
                    token_count INTEGER,
                    metadata_json TEXT,
                    FOREIGN KEY (document_id) REFERENCES documents(id)
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id)"
            )
            conn.commit()

    def insert_document(
        self,
        document_id: str,
        path: str | None = None,
        format_type: str | None = None,
        strategy: str | None = None,
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO documents (id, path, format, strategy) VALUES (?, ?, ?, ?)",
                (document_id, path or "", format_type or "", strategy or ""),
            )
            conn.commit()

    def insert_chunks(
        self,
        document_id: str,
        chunks: list[dict[str, Any]],
    ) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
            for c in chunks:
                meta_json = json.dumps(c.get("metadata", {}), ensure_ascii=False)
                conn.execute(
                    """INSERT INTO chunks (document_id, chunk_index, char_start, char_end, token_count, metadata_json)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        document_id,
                        c.get("index", 0),
                        c.get("start", 0),
                        c.get("end", 0),
                        c.get("token_count"),
                        meta_json,
                    ),
                )
            conn.commit()

    def get_chunks_by_document_id(self, document_id: str) -> list[dict[str, Any]]:
        with self._conn() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT document_id, chunk_index, char_start, char_end, token_count, metadata_json FROM chunks WHERE document_id = ? ORDER BY chunk_index",
                (document_id,),
            ).fetchall()
        out = []
        for r in rows:
            meta = {}
            if r["metadata_json"]:
                try:
                    meta = json.loads(r["metadata_json"])
                except json.JSONDecodeError:
                    pass
            out.append({
                "document_id": r["document_id"],
                "chunk_index": r["chunk_index"],
                "start": r["char_start"] or 0,
                "end": r["char_end"] or 0,
                "token_count": r["token_count"],
                "metadata": meta,
            })
        return out

    def get_document_metadata(self, document_id: str) -> dict[str, Any] | None:
        with self._conn() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT id, path, format, strategy, created_at FROM documents WHERE id = ?",
                (document_id,),
            ).fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "path": row["path"],
            "format": row["format"],
            "strategy": row["strategy"],
            "created_at": row["created_at"],
        }

    def delete_document(self, document_id: str) -> None:
        """Remove document and all its chunks from the store."""
        with self._conn() as conn:
            conn.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
            conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))
            conn.commit()
