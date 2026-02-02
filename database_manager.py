import sqlite3
import os
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

class DatabaseManager:
    def __init__(self):
        self.db_name = "metadata.db"
        self.vector_db_path = "faiss_index" 
        
        # Using OpenAI embedding model for strong Arabic language support
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        
        self._init_sql_db()

    def _init_sql_db(self):
        """Create SQL table to store metadata"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute(
            '''CREATE TABLE IF NOT EXISTS docs_metadata
               (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                filename TEXT, 
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                chunk_count INTEGER)'''
        )
        conn.commit()
        conn.close()

    def save_to_vector_db(self, chunks):
        """Save chunked documents to FAISS vector database"""
        vector_db = FAISS.from_documents(chunks, self.embeddings)
        vector_db.save_local(self.vector_db_path)
        return vector_db

    def save_metadata(self, filename, chunk_count):
        """Save file metadata to SQLite"""
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute(
            "INSERT INTO docs_metadata (filename, chunk_count) VALUES (?, ?)",
            (filename, chunk_count)
        )
        conn.commit()
        conn.close()

    def query_documents(self, question, k=3):
        """Search for the most relevant documents using FAISS"""
        index_file = os.path.join(self.vector_db_path, "index.faiss")
        if not os.path.exists(index_file):
            return []

        vector_db = FAISS.load_local(
            self.vector_db_path,
            self.embeddings,
            allow_dangerous_deserialization=True
        )
        
        # Perform similarity search and retrieve scores
        # Note: FAISS returns distance values, so we convert them to an approximate similarity score
        results = vector_db.similarity_search_with_score(question, k=k)
        
        formatted_results = []
        for doc, score in results:
            # Convert distance to an approximate relevance score (0–1)
            relevance_score = max(0, 1 - (score / 2))
            formatted_results.append((doc, relevance_score))
            
        return formatted_results
