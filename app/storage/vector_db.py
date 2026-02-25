import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any
import os

class VectorDB:
    def __init__(self, db_path: str = "data/vector_db"):
        """
        Initialize ChromaDB for semantic storage.
        """
        if not os.path.exists(db_path):
            os.makedirs(db_path)
            
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(name="document_chunks")

    def add_chunks(self, chunks: List[str], embeddings: List[List[float]], metadatas: List[Dict[str, Any]], ids: List[str]):
        """
        Add chunks with their embeddings and metadata to the vector store.
        """
        self.collection.add(
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas,
            ids=ids
        )

    def search(self, query_embedding: List[float], n_results: int = 3) -> Dict[str, Any]:
        """
        Search for the most similar chunks based on a query embedding.
        """
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        return results
