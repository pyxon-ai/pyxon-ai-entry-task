import re
from typing import List

class BenchmarkSuite:
    """
    A simple evaluation suite to measure:
    1. Retrieval Accuracy (Recall@K)
    2. Chunk Quality (Mid-sentence split detection)
    """

    def __init__(self, storage_manager):
        self.storage = storage_manager
        
    def evaluate_retrieval(self, query: str, expected_filename: str, top_k: int = 3) -> float:
        """
        Checks if the top_k results contain chunks from the expected document.
        Returns the proportion of relevant chunks in the top K.
        """
        results = self.storage.search(query, top_k=top_k)
        if not results:
            return 0.0
            
        relevant_count = sum(1 for res in results if res['metadata']['filename'] == expected_filename)
        return relevant_count / len(results)
        
    def evaluate_chunk_quality(self, chunks: List[str]) -> float:
        """
        Returns a score from 0.0 to 1.0 indicating chunk quality.
        Higher is better.
        Penalizes chunks that end mid-sentence (i.e. don't end with a punctuation).
        """
        if not chunks:
            return 1.0
            
        # Simple heuristic: Does the chunk end with punctuation?
        good_chunks = 0
        for chunk in chunks:
            chunk = chunk.strip()
            # If it's a heading or short string, it might not end in punctuation, but mostly sentences should.
            if chunk.endswith(('.', '!', '?', '؟', ':', '"', "'")):
                good_chunks += 1
            else:
                # Let's consider very short lines (like headings) acceptable even without punctuation
                if len(chunk) < 60:
                    good_chunks += 1
                    
        return good_chunks / len(chunks)

if __name__ == "__main__":
    print("Benchmark Suite ready.")
