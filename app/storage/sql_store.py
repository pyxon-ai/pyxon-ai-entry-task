import sqlite3


class SQLStore:
    def __init__(self, db_path: str = "docurag.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._create_tables()

    def _create_tables(self):
        cursor = self.conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT,
            language TEXT,
            num_chunks INTEGER,
            chunking_strategy TEXT
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id INTEGER,
            chunk_id INTEGER,
            text TEXT,
            FOREIGN KEY(doc_id) REFERENCES documents(id)
        )
        """)

        self.conn.commit()

    def insert_document(
        self,
        source: str,
        language: str,
        num_chunks: int,
        chunking_strategy: str
    ) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO documents (source, language, num_chunks, chunking_strategy)
            VALUES (?, ?, ?, ?)
            """,
            (source, language, num_chunks, chunking_strategy)
        )
        self.conn.commit()
        return cursor.lastrowid

    def insert_chunk(self, doc_id: int, chunk_id: int, text: str):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO chunks (doc_id, chunk_id, text)
            VALUES (?, ?, ?)
            """,
            (doc_id, chunk_id, text)
        )
        self.conn.commit()