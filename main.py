"""
Main RAG Pipeline - Orchestrates the entire document processing workflow
"""
import sys
import os

# Configure UTF-8 encoding for Windows console
# Configure UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import codecs
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    if hasattr(sys.stderr, 'buffer'):
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime

from core.arabic_processor import ArabicTextProcessor
from core.document_parser import DocumentParser
from core.chunking_strategy import FixedSizeChunker, SemanticChunker, AutoChunker
from core.embedding_manager import EmbeddingManager
from storage.vector_store import VectorStore
from storage.metadata_store import MetadataStore
from benchmarks.benchmark_suite import BenchmarkSuite
import config

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format=config.LOG_FORMAT
)
logger = logging.getLogger(__name__)


class ArabicRAGPipeline:
    """
    Main RAG Pipeline for Arabic Document Processing
    
    Orchestrates:
    - Document parsing (PDF/DOCX/TXT)
    - Arabic text processing (RTL, diacritics)
    - Intelligent chunking (fixed/semantic/auto)
    - Embedding generation
    - Vector storage (ChromaDB)
    - Metadata tracking (SQLite)
    """
    
    def __init__(
        self,
        vector_db_path: Optional[str] = None,
        metadata_db_path: Optional[str] = None,
        embedding_model: Optional[str] = None,
        chunking_strategy: str = 'auto',
        device: str = 'cpu'
    ):
        """
        Initialize RAG pipeline
        
        Args:
            vector_db_path: Path to ChromaDB directory
            metadata_db_path: Path to SQLite database
            embedding_model: Sentence-transformers model name
            chunking_strategy: 'fixed', 'semantic', or 'auto'
            device: 'cpu' or 'cuda'
        """
        logger.info("Initializing Arabic RAG Pipeline...")
        
        # Set paths
        self.vector_db_path = vector_db_path or config.CHROMA_DB_PATH
        self.metadata_db_path = metadata_db_path or str(config.SQLITE_DB_PATH)
        self.embedding_model_name = embedding_model or config.EMBEDDING_MODEL
        
        # Initialize components
        logger.info("Loading Arabic text processor...")
        self.arabic_processor = ArabicTextProcessor(preserve_diacritics=True)
        
        logger.info("Loading document parser...")
        self.parser = DocumentParser(self.arabic_processor)
        
        logger.info("Loading embedding manager...")
        self.embedding_manager = EmbeddingManager(
            model_name=self.embedding_model_name,
            device=device
        )
        
        logger.info("Initializing vector store...")
        self.vector_store = VectorStore(
            persist_directory=self.vector_db_path,
            embedding_dimension=self.embedding_manager.dimension
        )
        
        logger.info("Initializing metadata store...")
        self.metadata_store = MetadataStore(self.metadata_db_path)
        
        # Initialize chunking strategy
        logger.info(f"Setting up chunking strategy: {chunking_strategy}")
        self.chunking_strategy = self._get_chunker(chunking_strategy)
        
        # Benchmark suite
        self.benchmark_suite = BenchmarkSuite()
        
        logger.info("✅ Pipeline initialized successfully!")
    
    def _get_chunker(self, strategy: str):
        """Get chunking strategy instance"""
        if strategy == 'fixed':
            return FixedSizeChunker(
                chunk_size=config.ChunkingConfig.FIXED_CHUNK_SIZE,
                overlap=config.ChunkingConfig.FIXED_CHUNK_OVERLAP
            )
        elif strategy == 'semantic':
            return SemanticChunker(
                min_chunk_size=config.ChunkingConfig.SEMANTIC_MIN_CHUNK_SIZE,
                max_chunk_size=config.ChunkingConfig.SEMANTIC_MAX_CHUNK_SIZE,
                use_embeddings=False  # Use structure-based by default
            )
        elif strategy == 'auto':
            return AutoChunker()
        else:
            raise ValueError(f"Invalid chunking strategy: {strategy}")
    
    def process_document(
        self,
        file_path: str,
        custom_metadata: Optional[Dict] = None,
        status_callback: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Process a single document through the full pipeline
        
        Args:
            file_path: Path to document
            custom_metadata: Optional custom metadata
            status_callback: Optional callback function(str) for status updates
            
        Returns:
            Dictionary with processing results
        """
        logger.info(f"Processing document: {file_path}")
        
        if status_callback:
            status_callback("جاري التحضير...")
        
        file_path = Path(file_path)
        
        # Clean up existing metadata if re-processing
        self.metadata_store.delete_document_by_path(str(file_path))
        
        # 1. Parse document
        logger.info("Step 1: Parsing document...")
        if status_callback:
            status_callback("جاري قراءة الملف وتحليل النصوص...")
        doc_data = self.parser.parse(file_path)
        
        # 2. Chunk text
        logger.info("Step 2: Chunking text...")
        if status_callback:
            status_callback("جاري تقسيم النصوص (Chunking)...")
        chunks = self.chunking_strategy.chunk(
            text=doc_data['retrieval_text'],
            metadata={
                'file_path': str(file_path),
                'file_type': doc_data['file_type'],
                'is_arabic': doc_data['is_arabic'],
                **(custom_metadata or {})
            }
        )
        
        logger.info(f"Created {len(chunks)} chunks")
        
        # 3. Generate embeddings
        logger.info("Step 3: Generating embeddings...")
        if status_callback:
            status_callback(f"جاري إنشاء Embeddings لـ {len(chunks)} مقطع...")
        chunk_texts = [chunk.text for chunk in chunks]
        embeddings = self.embedding_manager.encode_batch(
            chunk_texts,
            show_progress=True
        )
        
        # 4. Store in vector database
        logger.info("Step 4: Storing in vector database...")
        if status_callback:
            status_callback("جاري الحفظ في قاعدة البيانات المتجهة...")
        chunk_metadatas = [chunk.metadata for chunk in chunks]
        chunk_ids = self.vector_store.add_chunks(
            chunks=chunk_texts,
            embeddings=embeddings,
            metadatas=chunk_metadatas
        )
        
        # 5. Store metadata in SQL database
        logger.info("Step 5: Storing metadata...")
        if status_callback:
            status_callback("جاري حفظ البيانات الوصفية...")
        doc_id = self.metadata_store.add_document(
            file_path=str(file_path),
            file_name=file_path.name,
            file_type=doc_data['file_type'],
            file_size=doc_data['file_size'],
            chunking_strategy=self.chunking_strategy.get_strategy_name(),
            num_chunks=len(chunks),
            is_arabic=doc_data['is_arabic'],
            encoding=doc_data.get('encoding'),
            extra_metadata={
                'entities': doc_data.get('entities', []),
                **(custom_metadata or {})
            }
        )
        
        # Store chunk metadata
        for i, (chunk, chunk_id) in enumerate(zip(chunks, chunk_ids)):
            self.metadata_store.add_chunk(
                chunk_id_vector=chunk_id,
                document_id=doc_id,
                chunk_index=i,
                start_idx=chunk.start_idx,
                end_idx=chunk.end_idx,
                text=chunk.text,
                chunk_metadata=chunk.metadata
            )
        
        logger.info(f"✅ Document processed successfully! Doc ID: {doc_id}")
        
        return {
            'doc_id': doc_id,
            'num_chunks': len(chunks),
            'chunk_ids': chunk_ids,
            'is_arabic': doc_data['is_arabic'],
            'chunking_strategy': self.chunking_strategy.get_strategy_name(),
        }
    
    def process_batch(
        self,
        file_paths: List[str],
        custom_metadata: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Process multiple documents
        
        Args:
            file_paths: List of file paths
            custom_metadata: Optional custom metadata for all documents
            
        Returns:
            List of processing results
        """
        logger.info(f"Processing batch of {len(file_paths)} documents...")
        
        results = []
        for i, file_path in enumerate(file_paths, 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing {i}/{len(file_paths)}: {file_path}")
            logger.info(f"{'='*60}")
            
            try:
                result = self.process_document(file_path, custom_metadata)
                results.append({
                    'file_path': file_path,
                    'success': True,
                    **result
                })
            except Exception as e:
                logger.error(f"Failed to process {file_path}: {e}", exc_info=True)
                results.append({
                    'file_path': file_path,
                    'success': False,
                    'error': str(e)
                })
        
        successful = sum(1 for r in results if r.get('success'))
        logger.info(f"\n✅ Batch processing complete: {successful}/{len(file_paths)} successful")
        
        return results
    
    def query(
        self,
        query_text: str,
        n_results: int = 5,
        filter_metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Query the RAG system
        
        Args:
            query_text: Query string
            n_results: Number of results to return
            filter_metadata: Optional metadata filter
            
        Returns:
            Query results with chunks and metadata
        """
        logger.info(f"Querying: '{query_text}'")
        
        # Process query text (especially if Arabic)
        processed_query = self.arabic_processor.process_text(query_text, mode='search')
        search_text = processed_query.get('search', query_text)
        
        # Generate query embedding
        query_embedding = self.embedding_manager.encode_single(search_text, is_query=True)
        
        # Query vector store
        results = self.vector_store.query(
            query_embedding=query_embedding,
            n_results=n_results,
            where=filter_metadata
        )
        
        # Enrich with metadata from SQL database
        chunk_ids = results['ids'][0] if results['ids'] else []
        
        logger.info(f"Found {len(chunk_ids)} results")
        
        return {
            'query': query_text,
            'processed_query': search_text,
            'results': results,
            'num_results': len(chunk_ids),
        }
    
    def run_benchmark(
        self,
        file_paths: List[str],
        test_queries: Optional[List[str]] = None,
        ground_truth_pdf: Optional[str] = None,
        ground_truth_txt: Optional[str] = None,
        run_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run benchmark suite on the pipeline
        
        Args:
            file_paths: Files to process for benchmarking
            test_queries: Test queries for retrieval benchmark
            ground_truth_pdf: Optional PDF for extraction accuracy
            ground_truth_txt: Optional ground truth text
            run_name: Name for benchmark run
            
        Returns:
            Benchmark results
        """
        if run_name is None:
            run_name = f"benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        if test_queries is None:
            test_queries = config.BenchmarkConfig.TEST_QUERIES
        
        logger.info(f"Running benchmark: {run_name}")
        
        # Run full benchmark
        result = self.benchmark_suite.run_full_benchmark(
            parser=self.parser,
            file_paths=file_paths,
            chunker=self.chunking_strategy,
            embedding_manager=self.embedding_manager,
            vector_store=self.vector_store,
            test_queries=test_queries,
            ground_truth_pdf=ground_truth_pdf,
            ground_truth_txt=ground_truth_txt,
            run_name=run_name
        )
        
        # Save to metadata store
        self.metadata_store.add_benchmark(
            run_name=result.run_name,
            processing_time=result.total_processing_time,
            memory_usage=result.peak_memory_mb,
            retrieval_accuracy=result.retrieval_accuracy,
            hit_rate=result.hit_rate,
            chunking_strategy=result.chunking_strategy,
            num_documents=result.num_documents,
            num_chunks=result.num_chunks,
            detailed_results=result.to_dict()
        )
        
        # Save to file
        output_file = config.OUTPUT_DIR / f"{run_name}.json"
        result.save_to_file(str(output_file))
        
        logger.info(f"✅ Benchmark complete! Results saved to {output_file}")
        
        return result.to_dict()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get pipeline statistics
        
        Returns:
            Dictionary with statistics
        """
        metadata_stats = self.metadata_store.get_stats()
        vector_stats = self.vector_store.get_info()
        
        return {
            'metadata_store': metadata_stats,
            'vector_store': vector_stats,
            'embedding_model': self.embedding_manager.get_model_info(),
            'chunking_strategy': self.chunking_strategy.get_strategy_name(),
        }
    
    def reset(self):
        """Reset the pipeline (clear all data)"""
        logger.warning("Resetting pipeline - this will delete all data!")
        self.vector_store.reset()
        self.metadata_store.reset()
        logger.info("Pipeline reset complete")


def main():
    """Example usage"""
    # Initialize pipeline
    pipeline = ArabicRAGPipeline(
        chunking_strategy='auto',
        device='cpu'
    )
    
    # Process documents
    files = [
        str(config.DATA_DIR / "file_ar.pdf"),
        str(config.DATA_DIR / "file.txt"),
    ]
    
    # Check which files exist
    existing_files = [f for f in files if Path(f).exists()]
    
    if existing_files:
        results = pipeline.process_batch(existing_files)
        
        # Query
        query_results = pipeline.query("ما هي خدمات إعادة التدوير؟", n_results=3)
        
        print("\n" + "="*60)
        print("Query Results:")
        print("="*60)
        for i, doc in enumerate(query_results['results']['documents'][0], 1):
            print(f"\n{i}. {doc[:200]}...")
        
        # Get stats
        stats = pipeline.get_stats()
        print("\n" + "="*60)
        print("Pipeline Statistics:")
        print("="*60)
        print(f"Total documents: {stats['metadata_store']['total_documents']}")
        print(f"Total chunks: {stats['metadata_store']['total_chunks']}")
        print(f"Arabic documents: {stats['metadata_store']['arabic_documents']}")
    else:
        logger.warning("No test files found. Please add files to the data directory.")
        logger.info(f"Expected files: {files}")


if __name__ == "__main__":
    main()
