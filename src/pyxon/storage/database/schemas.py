from datetime import datetime
from typing import List

from pydantic import BaseModel


class ChunkBase(BaseModel):
    chunk_index: int
    chunk_text: str


class ChunkCreate(ChunkBase):
    pass


class Chunk(ChunkBase):
    id: int
    doc_id: str

    class Config:
        from_attributes = True


class DocumentBase(BaseModel):
    filename: str
    source_path: str
    doc_type: str


class DocumentCreate(DocumentBase):
    pass


class Document(DocumentBase):
    id: str
    total_chunks: int
    created_at: datetime
    chunks: List[Chunk] = []

    class Config:
        from_attributes = True


class DocumentWithChunks(Document):
    chunks: List[Chunk]
