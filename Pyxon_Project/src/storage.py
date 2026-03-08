import os
import sqlite3
import uuid
import chromadb
from typing import List, Dict

class StorageManager:
    """
    Manages both SQL setup (SQLite) for document metadata & chunk relationships
    and Vector DB setup (ChromaDB) for chunk text and embeddings.
    """

    def __init__(self, db_dir: str = "data"):
        self.db_dir = db_dir
        if not os.path.exists(self.db_dir):
            os.makedirs(self.db_dir)
            
        # Initialize SQL DB
        self.sql_path = os.path.join(self.db_dir, "metadata.db")
        self._init_sql()

        # Initialize Vector DB (Chroma)
        self.chroma_client = chromadb.PersistentClient(path=os.path.join(self.db_dir, "chroma_db"))
        # We use a default embedding function provided by Chroma (all-MiniLM-L6-v2) 
        # or sentence-transformers underneath. We will just let Chroma handle embeddings 
        # out of the box for simplicity since it handles Arabic reasonably in newer models or we can configure it.
        # But to ensure Arabic support properly, we use a multilingual model from sentence-transformers
        from chromadb.utils import embedding_functions
        self.emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="paraphrase-multilingual-mpnet-base-v2")
        self.collection = self.chroma_client.get_or_create_collection(
            name="document_chunks_v2", 
            embedding_function=self.emb_fn
        )

    def _init_sql(self):
        """Create basic SQLite schema for metadata."""
        conn = sqlite3.connect(self.sql_path)
        cursor = conn.cursor()
        
        # Table for Documents
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                filename TEXT,
                strategy_used TEXT,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Table for Chunks (relationships and additional metadata)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY,
                doc_id TEXT,
                chunk_index INTEGER,
                FOREIGN KEY(doc_id) REFERENCES documents(id)
            )
        ''')
        conn.commit()
        conn.close()

    def store_document(self, filename: str, chunks: List[str], strategy: str) -> str:
        """
        Store the document and its chunks in both SQL and Vector databases.
        """
        doc_id = str(uuid.uuid4())
        
        # 1. Store Document Metadata in SQL
        conn = sqlite3.connect(self.sql_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO documents (id, filename, strategy_used) VALUES (?, ?, ?)", 
                       (doc_id, filename, strategy))
        
        # 2. Store Chunks
        chunk_ids = []
        metadatas = []
        documents = []
        
        for idx, chunk_text in enumerate(chunks):
            chunk_id = f"{doc_id}_chunk_{idx}"
            chunk_ids.append(chunk_id)
            documents.append(chunk_text)
            metadatas.append({"doc_id": doc_id, "chunk_index": idx, "filename": filename})
            
            # Store relationship in SQL
            cursor.execute("INSERT INTO chunks (id, doc_id, chunk_index) VALUES (?, ?, ?)",
                           (chunk_id, doc_id, idx))
            
        conn.commit()
        conn.close()
        
        # 3. Store in Vector DB
        if documents:
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=chunk_ids
            )
            
        return doc_id

    def search(self, query: str, top_k: int = 3, filter_filename: str = None) -> List[Dict]:
        """
        Search the vector database for the most relevant chunks.
        Optionally filter by a specific filename.
        """
        kwargs = {
            "query_texts": [query],
            "n_results": top_k
        }
        
        if filter_filename:
            kwargs["where"] = {"filename": filter_filename}
            
        results = self.collection.query(**kwargs)
        
        # Format results nicely
        formatted_results = []
        if results['documents'] and len(results['documents'][0]) > 0:
            docs = results['documents'][0]
            metadatas = results['metadatas'][0]
            for i in range(len(docs)):
                formatted_results.append({
                    "text": docs[i],
                    "metadata": metadatas[i]
                })
        return formatted_results

    def get_all_documents(self) -> List[str]:
        """
        Get a list of all unique filenames that have been processed.
        """
        conn = sqlite3.connect(self.sql_path)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT filename FROM documents ORDER BY uploaded_at DESC")
        rows = cursor.fetchall()
        conn.close()
        
        return [row[0] for row in rows]

if __name__ == "__main__":
    storage = StorageManager()
    print("Storage initialized.")
