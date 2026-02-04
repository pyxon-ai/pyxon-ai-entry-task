"""Document and chunk data models."""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class ChunkingStrategy(str, Enum):
    """Chunking strategy types."""
    FIXED = "fixed"
    DYNAMIC = "dynamic"
    AUTO = "auto"


class DocumentType(str, Enum):
    """Supported document types."""
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"


class DocumentMetadata(BaseModel):
    """Document metadata."""
    title: Optional[str] = None
    author: Optional[str] = None
    subject: Optional[str] = None
    keywords: Optional[List[str]] = None
    created_date: Optional[datetime] = None
    modified_date: Optional[datetime] = None
    page_count: Optional[int] = None
    word_count: Optional[int] = None
    language: Optional[str] = None
    has_arabic: bool = False
    has_diacritics: bool = False


class ChunkMetadata(BaseModel):
    """Chunk metadata."""
    chunk_index: int
    page_number: Optional[int] = None
    chunk_type: Optional[str] = None  # e.g., "heading", "paragraph", "table"
    heading: Optional[str] = None
    token_count: int
    char_count: int
    has_arabic: bool = False
    has_diacritics: bool = False


class Chunk(BaseModel):
    """Document chunk."""
    id: str
    document_id: str
    content: str
    metadata: ChunkMetadata
    embedding: Optional[List[float]] = None


class Document(BaseModel):
    """Processed document."""
    id: str
    filename: str
    file_type: DocumentType
    content: str
    metadata: DocumentMetadata
    chunks: List[Chunk] = []
    chunking_strategy: ChunkingStrategy = ChunkingStrategy.AUTO
    created_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None


class ProcessingResult(BaseModel):
    """Document processing result."""
    success: bool
    document: Optional[Document] = None
    error: Optional[str] = None
    processing_time: float = 0.0
    chunks_created: int = 0
