from typing import List


class FixedChunker:
    def __init__(self, chunk_size: int = 500):
        self.chunk_size = chunk_size

    def chunk(self, text: str) -> List[str]:
        chunks = []
        start = 0

        while start < len(text):
            end = start + self.chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start = end

        return chunks