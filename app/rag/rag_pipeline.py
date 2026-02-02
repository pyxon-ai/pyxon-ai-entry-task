from app.retrieval.retriever import Retriever

class RAGPipeline:
    def __init__(self):
        self.retriever = Retriever()

    def run(self, query: str):
        """
        RAG-ready pipeline:
        1. Retrieve relevant chunks
        2. (Optional) Pass them to an LLM for generation
        """
        retrieved_chunks = self.retriever.retrieve(query)

        # For now, we return retrieved chunks only
        # LLM integration can be added later
        return {
            "query": query,
            "retrieved_chunks": retrieved_chunks
        }