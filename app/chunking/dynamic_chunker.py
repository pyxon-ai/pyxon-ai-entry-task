from typing import List


class DynamicChunker:
    def __init__(self, max_chunk_size: int = 800):
        self.max_chunk_size = max_chunk_size

    def chunk(self, text: str) -> List[str]:
        paragraphs = [p for p in text.split("\n") if p.strip()]
        chunks = []
        current_chunk = ""

        for paragraph in paragraphs:
            if len(current_chunk) + len(paragraph) <= self.max_chunk_size:
                current_chunk += paragraph + "\n"
            else:
                chunks.append(current_chunk.strip())
                current_chunk = paragraph + "\n"

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks