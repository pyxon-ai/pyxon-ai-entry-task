import os
import uuid
import chromadb


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
CHROMA_PATH = os.path.join(BASE_DIR, "chroma_db")


class VectorStore:
    def __init__(self, collection_name: str = "documents"):
        self.client = chromadb.PersistentClient(
            path=CHROMA_PATH
        )
        self.collection = self.client.get_or_create_collection(
            name=collection_name
        )

    def add_vector(self, vector, text: str, metadata: dict):
        self.collection.add(
            embeddings=[vector.tolist()],
            documents=[text],
            metadatas=[metadata],
            ids=[str(uuid.uuid4())]
        )

    def query(self, query_vector, top_k: int = 5):
        return self.collection.query(
            query_embeddings=[query_vector.tolist()],
            n_results=top_k
        )