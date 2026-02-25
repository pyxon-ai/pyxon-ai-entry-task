import sqlite3
from typing import List, Dict, Any
import os

class SQLDB:
    def __init__(self, db_path: str = "data/metadata.db"):
        """
        Initialize SQLite for structured metadata storage.
        """
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
            
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._create_tables()
        self._migrate_tables()

    def _migrate_tables(self):
        """Ensure schema is up to date."""
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT heading FROM chunks LIMIT 1")
        except sqlite3.OperationalError:
            # Column missing, add it
            cursor.execute("ALTER TABLE chunks ADD COLUMN heading TEXT")
            self.conn.commit()

    def _create_tables(self):
        """Create necessary tables if they don't exist."""
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                filename TEXT,
                file_type TEXT,
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY,
                document_id TEXT,
                chunk_index INTEGER,
                content TEXT,
                heading TEXT,
                FOREIGN KEY (document_id) REFERENCES documents (id)
            )
        ''')
        self.conn.commit()

    def add_document(self, doc_id: str, filename: str, file_type: str):
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO documents (id, filename, file_type) VALUES (?, ?, ?)",
            (doc_id, filename, file_type)
        )
        self.conn.commit()

    def add_chunk(self, chunk_id: str, doc_id: str, index: int, content: str, heading: str = None):
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO chunks (id, document_id, chunk_index, content, heading) VALUES (?, ?, ?, ?, ?)",
            (chunk_id, doc_id, index, content, heading)
        )
        self.conn.commit()

    def get_document_metadata(self, doc_id: str):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
        return cursor.fetchone()

    def get_chunks(self, doc_id: str):
        """Retrieve all chunks for a document ordered by index."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT content, heading FROM chunks WHERE document_id = ? ORDER BY chunk_index", (doc_id,))
        return cursor.fetchall()
