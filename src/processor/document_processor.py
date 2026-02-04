"""Main document processor that integrates all components."""

import time
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from src.config.settings import settings
from src.models.document import Document, ProcessingResult
from src.parsers.docling_parser import DoclingParser
from src.chunking.strategies import IntelligentChunker, FixedChunker, DynamicChunker
from src.embeddings.generator import get_embedding_generator
from src.arabic.processor import get_arabic_processor
from src.database.connection import db_manager
from src.database.repository import DocumentRepository, ChunkRepository


class DocumentProcessor:
    """Main document processor that integrates parsing, chunking, and storage."""

    def __init__(self, session: Session):
        self.session = session
        self.parser = DoclingParser()
        
        # Initialize chunkers
        self.fixed_chunker = FixedChunker(
            chunk_size=settings.chunk_size,
            overlap=settings.chunk_overlap,
        )
        self.dynamic_chunker = DynamicChunker(
            max_chunk_size=1000,
            min_chunk_size=200,
        )
        self.intelligent_chunker = IntelligentChunker(
            fixed_chunker=self.fixed_chunker,
            dynamic_chunker=self.dynamic_chunker,
        )
        
        # Initialize embedding generator
        self.embedding_generator = get_embedding_generator()
        
        # Initialize Arabic processor
        self.arabic_processor = get_arabic_processor()
        
        # Initialize repositories
        self.document_repo = DocumentRepository(session)
        self.chunk_repo = ChunkRepository(session)

    def process_file(
        self,
        file_path: str,
        chunking_strategy: Optional[str] = None,
    ) -> ProcessingResult:
        """
        Process a document file end-to-end.
        
        Args:
            file_path: Path to document file
            chunking_strategy: Optional chunking strategy ('fixed', 'dynamic', 'auto')
        
        Returns:
            ProcessingResult with document and metadata
        """
        start_time = time.time()
        
        try:
            # Parse document
            document = self.parser.parse_file(file_path)
            
            # Apply chunking strategy
            if chunking_strategy == "fixed":
                document.chunks = self.fixed_chunker.chunk(document)
                document.chunking_strategy = "fixed"
            elif chunking_strategy == "dynamic":
                document.chunks = self.dynamic_chunker.chunk(document)
                document.chunking_strategy = "dynamic"
            else:
                # Auto-detect best strategy
                document.chunks = self.intelligent_chunker.chunk(document)
            
            # Generate embeddings for chunks
            if document.chunks:
                self.embedding_generator.embed_chunks(document.chunks)
            
            # Store in database
            self.document_repo.create_document(document)
            if document.chunks:
                self.chunk_repo.create_chunks(document.chunks)
            
            processing_time = time.time() - start_time
            
            return ProcessingResult(
                success=True,
                document=document,
                processing_time=processing_time,
                chunks_created=len(document.chunks),
            )
        
        except Exception as e:
            processing_time = time.time() - start_time
            return ProcessingResult(
                success=False,
                error=str(e),
                processing_time=processing_time,
                chunks_created=0,
            )

    def process_text(
        self,
        text: str,
        filename: str = "text.txt",
        chunking_strategy: Optional[str] = None,
    ) -> ProcessingResult:
        """
        Process raw text content.
        
        Args:
            text: Text content to process
            filename: Filename to use for the document
            chunking_strategy: Optional chunking strategy
        
        Returns:
            ProcessingResult with document and metadata
        """
        start_time = time.time()
        
        try:
            # Parse text
            document = self.parser.parse_text(text, filename)
            
            # Apply chunking strategy
            if chunking_strategy == "fixed":
                document.chunks = self.fixed_chunker.chunk(document)
                document.chunking_strategy = "fixed"
            elif chunking_strategy == "dynamic":
                document.chunks = self.dynamic_chunker.chunk(document)
                document.chunking_strategy = "dynamic"
            else:
                # Auto-detect best strategy
                document.chunks = self.intelligent_chunker.chunk(document)
            
            # Generate embeddings for chunks
            if document.chunks:
                self.embedding_generator.embed_chunks(document.chunks)
            
            # Store in database
            self.document_repo.create_document(document)
            if document.chunks:
                self.chunk_repo.create_chunks(document.chunks)
            
            processing_time = time.time() - start_time
            
            return ProcessingResult(
                success=True,
                document=document,
                processing_time=processing_time,
                chunks_created=len(document.chunks),
            )
        
        except Exception as e:
            processing_time = time.time() - start_time
            return ProcessingResult(
                success=False,
                error=str(e),
                processing_time=processing_time,
                chunks_created=0,
            )

    def get_document(self, document_id: str) -> Optional[Document]:
        """Get a processed document by ID."""
        doc_model = self.document_repo.get_document(document_id)
        if not doc_model:
            return None
        
        # Get chunks
        chunk_models = self.chunk_repo.get_chunks_by_document(document_id)
        
        # Convert to Document model
        from src.models.document import Document, Chunk, ChunkMetadata
        
        chunks = [
            Chunk(
                id=cm.id,
                document_id=cm.document_id,
                content=cm.content,
                metadata=ChunkMetadata(
                    chunk_index=cm.chunk_index,
                    page_number=cm.page_number,
                    chunk_type=cm.chunk_type,
                    heading=cm.heading,
                    token_count=cm.token_count,
                    char_count=cm.char_count,
                    has_arabic=cm.has_arabic,
                    has_diacritics=cm.has_diacritics,
                ),
                embedding=cm.embedding,
            )
            for cm in chunk_models
        ]
        
        from src.models.document import DocumentMetadata
        document = Document(
            id=doc_model.id,
            filename=doc_model.filename,
            file_type=doc_model.file_type,
            content=doc_model.content,
            metadata=DocumentMetadata(
                title=doc_model.title,
                author=doc_model.author,
                subject=doc_model.subject,
                keywords=doc_model.keywords,
                created_date=doc_model.created_date,
                modified_date=doc_model.modified_date,
                page_count=doc_model.page_count,
                word_count=doc_model.word_count,
                language=doc_model.language,
                has_arabic=doc_model.has_arabic,
                has_diacritics=doc_model.has_diacritics,
            ),
            chunks=chunks,
            chunking_strategy=doc_model.chunking_strategy,
            created_at=doc_model.created_at,
            processed_at=doc_model.processed_at,
        )
        
        return document

    def list_documents(self, skip: int = 0, limit: int = 100):
        """List all processed documents."""
        return self.document_repo.get_all_documents(skip=skip, limit=limit)

    def delete_document(self, document_id: str) -> bool:
        """Delete a document and its chunks."""
        return self.document_repo.delete_document(document_id)
