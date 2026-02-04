"""
Comprehensive Benchmarking Suite for RAG System
Measures: Retrieval Accuracy, Processing Time, Memory Usage
"""
import logging
import time
import psutil
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import json

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """Container for benchmark results"""
    run_name: str
    timestamp: str
    
    # Performance metrics
    total_processing_time: float  # seconds
    avg_chunk_time: float  # seconds per chunk
    peak_memory_mb: float
    avg_memory_mb: float
    
    # Quality metrics
    retrieval_accuracy: float  # 0-1
    hit_rate: float  # 0-1
    mrr: float = 0.0  # Mean Reciprocal Rank
    
    # Configuration
    chunking_strategy: str = ""
    num_documents: int = 0
    num_chunks: int = 0
    
    # Detailed results
    query_results: List[Dict] = field(default_factory=list)
    timing_breakdown: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'run_name': self.run_name,
            'timestamp': self.timestamp,
            'performance': {
                'total_processing_time': self.total_processing_time,
                'avg_chunk_time': self.avg_chunk_time,
                'peak_memory_mb': self.peak_memory_mb,
                'avg_memory_mb': self.avg_memory_mb,
            },
            'quality': {
                'retrieval_accuracy': self.retrieval_accuracy,
                'hit_rate': self.hit_rate,
                'mrr': self.mrr,
            },
            'configuration': {
                'chunking_strategy': self.chunking_strategy,
                'num_documents': self.num_documents,
                'num_chunks': self.num_chunks,
            },
            'query_results': self.query_results,
            'timing_breakdown': self.timing_breakdown,
        }
    
    def save_to_file(self, filepath: str):
        """Save results to JSON file"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        logger.info(f"Saved benchmark results to {filepath}")


class BenchmarkSuite:
    """
    Comprehensive benchmarking suite for RAG system
    """
    
    def __init__(self):
        """Initialize benchmark suite"""
        self.process = psutil.Process()
        self.memory_samples = []
    
    def _start_memory_monitoring(self):
        """Start monitoring memory usage"""
        self.memory_samples = []
        self.memory_samples.append(self.process.memory_info().rss / 1024 / 1024)  # MB
    
    def _sample_memory(self):
        """Sample current memory usage"""
        self.memory_samples.append(self.process.memory_info().rss / 1024 / 1024)
    
    def _get_memory_stats(self) -> Tuple[float, float]:
        """
        Get memory statistics
        
        Returns:
            Tuple of (peak_memory_mb, avg_memory_mb)
        """
        if not self.memory_samples:
            return 0.0, 0.0
        
        return max(self.memory_samples), np.mean(self.memory_samples)
    
    def benchmark_processing(
        self,
        parser,
        file_paths: List[str],
        chunker,
        embedding_manager
    ) -> Dict[str, Any]:
        """
        Benchmark document processing pipeline
        
        Args:
            parser: DocumentParser instance
            file_paths: List of files to process
            chunker: Chunking strategy instance
            embedding_manager: EmbeddingManager instance
            
        Returns:
            Dictionary with processing metrics
        """
        logger.info(f"Benchmarking processing for {len(file_paths)} documents")
        
        self._start_memory_monitoring()
        
        timings = {
            'parsing': [],
            'chunking': [],
            'embedding': [],
        }
        
        total_chunks = 0
        
        # Process each document
        for file_path in file_paths:
            # Parsing
            t0 = time.time()
            doc_data = parser.parse(file_path)
            t1 = time.time()
            timings['parsing'].append(t1 - t0)
            
            self._sample_memory()
            
            # Chunking
            t0 = time.time()
            chunks = chunker.chunk(doc_data['retrieval_text'])
            t1 = time.time()
            timings['chunking'].append(t1 - t0)
            total_chunks += len(chunks)
            
            self._sample_memory()
            
            # Embedding
            t0 = time.time()
            chunk_texts = [c.text for c in chunks]
            embeddings = embedding_manager.encode_batch(chunk_texts, show_progress=False)
            t1 = time.time()
            timings['embedding'].append(t1 - t0)
            
            self._sample_memory()
        
        # Calculate statistics
        peak_mem, avg_mem = self._get_memory_stats()
        
        results = {
            'total_time': sum(timings['parsing']) + sum(timings['chunking']) + sum(timings['embedding']),
            'avg_parsing_time': np.mean(timings['parsing']),
            'avg_chunking_time': np.mean(timings['chunking']),
            'avg_embedding_time': np.mean(timings['embedding']),
            'total_chunks': total_chunks,
            'avg_chunks_per_doc': total_chunks / len(file_paths) if file_paths else 0,
            'peak_memory_mb': peak_mem,
            'avg_memory_mb': avg_mem,
            'timing_breakdown': {
                'parsing': sum(timings['parsing']),
                'chunking': sum(timings['chunking']),
                'embedding': sum(timings['embedding']),
            }
        }
        
        logger.info(f"Processing benchmark complete: {results['total_time']:.2f}s, {total_chunks} chunks")
        
        return results
    
    def benchmark_retrieval(
        self,
        vector_store,
        embedding_manager,
        test_queries: List[str],
        ground_truth: Optional[Dict[str, List[str]]] = None,
        k: int = 5
    ) -> Dict[str, Any]:
        """
        Benchmark retrieval accuracy
        
        Args:
            vector_store: VectorStore instance
            embedding_manager: EmbeddingManager instance
            test_queries: List of test queries
            ground_truth: Optional dictionary mapping queries to relevant chunk IDs
            k: Number of results to retrieve
            
        Returns:
            Dictionary with retrieval metrics
        """
        logger.info(f"Benchmarking retrieval for {len(test_queries)} queries")
        
        query_results = []
        retrieval_times = []
        hits = 0
        reciprocal_ranks = []
        
        for query in test_queries:
            # Encode query
            t0 = time.time()
            query_embedding = embedding_manager.encode_single(query)
            
            # Query vector store
            results = vector_store.query(query_embedding, n_results=k)
            t1 = time.time()
            
            retrieval_times.append(t1 - t0)
            
            # Check against ground truth if provided
            hit = False
            rank = 0
            
            if ground_truth and query in ground_truth:
                relevant_ids = set(ground_truth[query])
                retrieved_ids = results['ids'][0] if results['ids'] else []
                
                # Check for hits
                for i, retrieved_id in enumerate(retrieved_ids):
                    if retrieved_id in relevant_ids:
                        hit = True
                        if rank == 0:  # First hit
                            rank = i + 1
                        break
                
                if hit:
                    hits += 1
                    reciprocal_ranks.append(1.0 / rank if rank > 0 else 0.0)
            
            query_results.append({
                'query': query,
                'retrieval_time': t1 - t0,
                'hit': hit,
                'rank': rank,
                'num_results': len(results['ids'][0]) if results['ids'] else 0,
            })
        
        # Calculate metrics
        hit_rate = hits / len(test_queries) if test_queries else 0.0
        mrr = np.mean(reciprocal_ranks) if reciprocal_ranks else 0.0
        avg_retrieval_time = np.mean(retrieval_times) if retrieval_times else 0.0
        
        results = {
            'hit_rate': hit_rate,
            'mrr': mrr,
            'avg_retrieval_time': avg_retrieval_time,
            'total_queries': len(test_queries),
            'hits': hits,
            'query_results': query_results,
        }
        
        logger.info(f"Retrieval benchmark complete: Hit Rate={hit_rate:.2%}, MRR={mrr:.3f}")
        
        return results
    
    def benchmark_arabic_extraction(
        self,
        parser,
        pdf_file: str,
        ground_truth_file: str
    ) -> Dict[str, Any]:
        """
        Benchmark Arabic text extraction accuracy
        Compare PDF extraction against ground truth text file
        
        Args:
            parser: DocumentParser instance
            pdf_file: Path to PDF file
            ground_truth_file: Path to ground truth text file
            
        Returns:
            Dictionary with extraction accuracy metrics
        """
        logger.info(f"Benchmarking Arabic extraction: {pdf_file}")
        
        # Parse PDF
        pdf_data = parser.parse(pdf_file)
        pdf_text = pdf_data['retrieval_text']
        
        # Load ground truth
        with open(ground_truth_file, 'r', encoding='utf-8') as f:
            ground_truth_text = f.read()
        
        # Simple character-level accuracy
        # This is a basic metric - could be improved with edit distance
        min_len = min(len(pdf_text), len(ground_truth_text))
        max_len = max(len(pdf_text), len(ground_truth_text))
        
        matching_chars = sum(
            1 for i in range(min_len) 
            if i < len(pdf_text) and i < len(ground_truth_text) 
            and pdf_text[i] == ground_truth_text[i]
        )
        
        # Character accuracy
        char_accuracy = matching_chars / max_len if max_len > 0 else 0.0
        
        # Word-level comparison
        pdf_words = set(pdf_text.split())
        truth_words = set(ground_truth_text.split())
        
        word_overlap = len(pdf_words & truth_words)
        word_precision = word_overlap / len(pdf_words) if pdf_words else 0.0
        word_recall = word_overlap / len(truth_words) if truth_words else 0.0
        word_f1 = 2 * word_precision * word_recall / (word_precision + word_recall) if (word_precision + word_recall) > 0 else 0.0
        
        results = {
            'char_accuracy': char_accuracy,
            'word_precision': word_precision,
            'word_recall': word_recall,
            'word_f1': word_f1,
            'pdf_length': len(pdf_text),
            'truth_length': len(ground_truth_text),
            'pdf_words': len(pdf_words),
            'truth_words': len(truth_words),
            'word_overlap': word_overlap,
        }
        
        logger.info(
            f"Extraction accuracy: Char={char_accuracy:.2%}, "
            f"Word F1={word_f1:.2%}"
        )
        
        return results
    
    def run_full_benchmark(
        self,
        parser,
        file_paths: List[str],
        chunker,
        embedding_manager,
        vector_store,
        test_queries: List[str],
        ground_truth_pdf: Optional[str] = None,
        ground_truth_txt: Optional[str] = None,
        run_name: str = "benchmark_run"
    ) -> BenchmarkResult:
        """
        Run complete benchmark suite
        
        Args:
            parser: DocumentParser instance
            file_paths: List of files to process
            chunker: Chunking strategy instance
            embedding_manager: EmbeddingManager instance
            vector_store: VectorStore instance
            test_queries: List of test queries
            ground_truth_pdf: Optional PDF for extraction accuracy test
            ground_truth_txt: Optional ground truth text
            run_name: Name for this benchmark run
            
        Returns:
            BenchmarkResult object
        """
        from datetime import datetime
        
        logger.info(f"Starting full benchmark: {run_name}")
        
        # 1. Processing benchmark
        processing_results = self.benchmark_processing(
            parser, file_paths, chunker, embedding_manager
        )
        
        # 2. Retrieval benchmark
        retrieval_results = self.benchmark_retrieval(
            vector_store, embedding_manager, test_queries
        )
        
        # 3. Arabic extraction accuracy (if ground truth provided)
        extraction_results = None
        if ground_truth_pdf and ground_truth_txt:
            extraction_results = self.benchmark_arabic_extraction(
                parser, ground_truth_pdf, ground_truth_txt
            )
        
        # Compile results
        result = BenchmarkResult(
            run_name=run_name,
            timestamp=datetime.now().isoformat(),
            total_processing_time=processing_results['total_time'],
            avg_chunk_time=processing_results['total_time'] / processing_results['total_chunks'] if processing_results['total_chunks'] > 0 else 0.0,
            peak_memory_mb=processing_results['peak_memory_mb'],
            avg_memory_mb=processing_results['avg_memory_mb'],
            retrieval_accuracy=extraction_results['word_f1'] if extraction_results else 0.0,
            hit_rate=retrieval_results['hit_rate'],
            mrr=retrieval_results['mrr'],
            chunking_strategy=chunker.get_strategy_name(),
            num_documents=len(file_paths),
            num_chunks=processing_results['total_chunks'],
            query_results=retrieval_results['query_results'],
            timing_breakdown=processing_results['timing_breakdown'],
        )
        
        logger.info(f"Benchmark complete: {run_name}")
        
        return result
