from .fixed_chunker import FixedChunker
from .dynamic_chunker import DynamicChunker


class ChunkSelector:
    def __init__(self):
        self.fixed_chunker = FixedChunker()
        self.dynamic_chunker = DynamicChunker()

    def select_and_chunk(self, text: str, analysis: dict):
        """
        Decide which chunking strategy to use based on content analysis.
        """

        # Heuristic decision
        if analysis["num_headings"] > 3 or analysis["avg_paragraph_length"] > 300:
            strategy = "dynamic"
            chunks = self.dynamic_chunker.chunk(text)
        else:
            strategy = "fixed"
            chunks = self.fixed_chunker.chunk(text)

        return {
            "strategy": strategy,
            "num_chunks": len(chunks),
            "chunks": chunks
        }