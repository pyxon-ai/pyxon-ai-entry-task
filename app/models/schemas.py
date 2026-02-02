"""Pydantic schemas for API request/response validation"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class DocumentUploadResponse(BaseModel):
    """Response after document upload"""
    document_id: str
    filename: str
    file_type: str
    file_size: int
    language: str
    chunking_strategy: str
    total_chunks: int
    message: str


class DocumentMetadata(BaseModel):
    """Document metadata schema"""
    model_config = {
        'from_attributes': True,
        'populate_by_name': True
    }
    
    id: str
    filename: str
    file_type: str
    file_size: int
    language: str
    chunking_strategy: str
    total_chunks: int
    upload_date: datetime
    metadata: Optional[Dict[str, Any]] = Field(None, alias='doc_metadata')


class ChunkSchema(BaseModel):
    """Chunk schema"""
    model_config = {
        'from_attributes': True,
        'populate_by_name': True
    }
    
    id: str
    document_id: str
    chunk_index: int
    chunk_text: str
    chunk_size: int
    metadata: Optional[Dict[str, Any]] = Field(None, alias='chunk_metadata')


class QueryRequest(BaseModel):
    """Query request schema"""
    query: str = Field(..., min_length=1, description="Search query")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of results to return")
    document_id: Optional[str] = Field(None, description="Filter by specific document")
    language: Optional[str] = Field(None, description="Filter by language")


class QueryResult(BaseModel):
    """Individual query result"""
    chunk_id: str
    document_id: str
    document_name: str
    chunk_text: str
    similarity_score: float
    chunk_index: int


class QueryResponse(BaseModel):
    """Query response schema"""
    query: str
    results: List[QueryResult]
    total_results: int
    processing_time: float


class BenchmarkResult(BaseModel):
    """Benchmark result schema"""
    test_name: str
    metric: str
    score: float
    details: Optional[Dict[str, Any]] = None
