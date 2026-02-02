"""
Document API Endpoints
Handles document upload, processing, and management
"""

import os
import shutil
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException
from loguru import logger

from app.models.schemas import DocumentUploadResponse, DocumentMetadata
from app.services import (
    DocumentProcessor,
    ChunkingService,
    EmbeddingService,
    StorageService
)
from app.config import settings

router = APIRouter(prefix="/api/documents", tags=["documents"])

# Initialize services
doc_processor = DocumentProcessor()
chunking_service = ChunkingService(
    default_chunk_size=settings.default_chunk_size,
    default_overlap=settings.default_chunk_overlap
)
embedding_service = EmbeddingService(model_name=settings.embedding_model)
storage_service = StorageService()

# Create upload directory
os.makedirs(settings.upload_dir, exist_ok=True)


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload and process a document
    
    Supports: PDF, DOCX, DOC, TXT
    """
    try:
        # Validate file type
        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension not in ['.pdf', '.docx', '.doc', '.txt']:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file_extension}. Supported: PDF, DOCX, DOC, TXT"
            )
        
        # Save uploaded file
        file_path = os.path.join(settings.upload_dir, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"Processing uploaded file: {file.filename}")
        
        # Process document
        doc_metadata = doc_processor.process_file(file_path)
        
        # Chunk the text
        chunks = chunking_service.chunk_text(
            text=doc_metadata['text'],
            strategy='auto',
            metadata=doc_metadata
        )
        
        # Determine chunking strategy used
        chunking_strategy = chunks[0].metadata.get('strategy', 'unknown') if chunks else 'none'
        
        # Generate embeddings for chunks
        chunk_texts = [chunk.text for chunk in chunks]
        embeddings = embedding_service.generate_embeddings_batch(chunk_texts)
        
        # Store document metadata
        document_id = storage_service.store_document(
            filename=doc_metadata['filename'],
            file_type=doc_metadata['file_type'],
            file_size=doc_metadata['file_size'],
            language=doc_metadata['language'],
            chunking_strategy=chunking_strategy,
            total_chunks=len(chunks),
            metadata={
                'page_count': doc_metadata.get('page_count', 0),
                'has_arabic_diacritics': doc_metadata.get('has_arabic_diacritics', False),
                'character_count': doc_metadata.get('character_count', 0),
                'word_count': doc_metadata.get('word_count', 0)
            }
        )
        
        # Store chunks with embeddings
        chunk_data = [
            {
                'text': chunk.text,
                'index': chunk.index,
                'metadata': chunk.metadata
            }
            for chunk in chunks
        ]
        storage_service.store_chunks(document_id, chunk_data, embeddings)
        
        logger.info(f"Successfully processed document: {document_id}")
        
        return DocumentUploadResponse(
            document_id=document_id,
            filename=doc_metadata['filename'],
            file_type=doc_metadata['file_type'],
            file_size=doc_metadata['file_size'],
            language=doc_metadata['language'],
            chunking_strategy=chunking_strategy,
            total_chunks=len(chunks),
            message=f"Document processed successfully with {len(chunks)} chunks"
        )
    
    except Exception as e:
        logger.error(f"Error processing document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[DocumentMetadata], response_model_by_alias=False)
async def list_documents():
    """Get all documents"""
    try:
        documents = storage_service.get_all_documents()
        return documents
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}", response_model=DocumentMetadata, response_model_by_alias=False)
async def get_document(document_id: str):
    """Get document by ID"""
    try:
        document = storage_service.get_document(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        return document
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{document_id}")
async def delete_document(document_id: str):
    """Delete document and all its chunks"""
    try:
        document = storage_service.get_document(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        storage_service.delete_document(document_id)
        
        return {"message": f"Document {document_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(status_code=500, detail=str(e))
