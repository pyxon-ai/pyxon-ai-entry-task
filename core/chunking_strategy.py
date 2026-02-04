"""
Intelligent Chunking Strategies for Arabic RAG
Implements: Fixed-size, Semantic, and Auto-selector chunking
"""
import re
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """Represents a text chunk with metadata"""
    text: str
    start_idx: int
    end_idx: int
    chunk_id: int
    metadata: Dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ChunkingStrategy(ABC):
    """Abstract base class for chunking strategies"""
    
    @abstractmethod
    def chunk(self, text: str, metadata: Dict = None) -> List[Chunk]:
        """Chunk text into segments"""
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """Return strategy name for tracking"""
        pass


class FixedSizeChunker(ChunkingStrategy):
    """
    Fixed-size chunking with configurable overlap
    Simple and reliable for uniform content
    """
    
    def __init__(self, chunk_size: int = 512, overlap: int = 128):
        """
        Initialize fixed-size chunker
        
        Args:
            chunk_size: Number of characters per chunk
            overlap: Number of overlapping characters between chunks
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        
        if overlap >= chunk_size:
            raise ValueError("Overlap must be less than chunk_size")
    
    def chunk(self, text: str, metadata: Dict = None) -> List[Chunk]:
        """
        Chunk text into fixed-size segments with overlap
        
        Args:
            text: Text to chunk
            metadata: Optional metadata to attach to chunks
            
        Returns:
            List of Chunk objects
        """
        if metadata is None:
            metadata = {}
        
        chunks = []
        text_length = len(text)
        chunk_id = 0
        
        # Calculate step size
        step = self.chunk_size - self.overlap
        
        for i in range(0, text_length, step):
            end_idx = min(i + self.chunk_size, text_length)
            chunk_text = text[i:end_idx]
            
            # Skip empty or whitespace-only chunks
            if chunk_text.strip():
                chunk = Chunk(
                    text=chunk_text,
                    start_idx=i,
                    end_idx=end_idx,
                    chunk_id=chunk_id,
                    metadata={
                        **metadata,
                        'strategy': self.get_strategy_name(),
                        'chunk_size': self.chunk_size,
                        'overlap': self.overlap,
                    }
                )
                chunks.append(chunk)
                chunk_id += 1
            
            # Break if we've reached the end
            if end_idx >= text_length:
                break
        
        logger.info(f"Created {len(chunks)} chunks using fixed-size strategy")
        return chunks
    
    def get_strategy_name(self) -> str:
        return "fixed_size"


class SemanticChunker(ChunkingStrategy):
    """
    Semantic/Dynamic chunking based on content structure
    Identifies headers, paragraphs, and semantic boundaries
    """
    
    def __init__(
        self,
        min_chunk_size: int = 200,
        max_chunk_size: int = 1000,
        use_embeddings: bool = False,
        model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"
    ):
        """
        Initialize semantic chunker
        
        Args:
            min_chunk_size: Minimum characters per chunk
            max_chunk_size: Maximum characters per chunk
            use_embeddings: Whether to use embeddings for similarity-based chunking
            model_name: Embedding model name
        """
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.use_embeddings = use_embeddings
        
        # Initialize embedding model if needed
        self.model = None
        if use_embeddings:
            logger.info(f"Loading embedding model: {model_name}")
            self.model = SentenceTransformer(model_name)
        
        # Patterns for detecting structure
        self.header_patterns = [
            r'^#{1,6}\s+.+$',  # Markdown headers
            r'^.{0,100}:$',  # Lines ending with colon (often headers in Arabic)
            r'^\d+\.\s+.+$',  # Numbered headers
            r'^[A-Z\u0600-\u06FF].{0,80}$',  # Short lines (potential headers)
        ]
    
    def detect_headers(self, lines: List[str]) -> List[int]:
        """
        Detect header lines in text
        
        Args:
            lines: List of text lines
            
        Returns:
            List of line indices that are headers
        """
        header_indices = []
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
            
            # Check against header patterns
            for pattern in self.header_patterns:
                if re.match(pattern, line, re.MULTILINE):
                    header_indices.append(i)
                    break
            
            # Additional heuristic: very short lines might be headers
            if len(line) < 80 and len(line) > 3:
                # Check if next line is much longer (content)
                if i + 1 < len(lines) and len(lines[i + 1].strip()) > len(line) * 2:
                    header_indices.append(i)
        
        return header_indices
    
    def chunk_by_structure(self, text: str, metadata: Dict = None) -> List[Chunk]:
        """
        Chunk text based on structural elements (headers, paragraphs)
        Handles both Unix (\n) and Windows (\r\n) line endings
        
        Args:
            text: Text to chunk
            metadata: Optional metadata
            
        Returns:
            List of Chunk objects
        """
        if metadata is None:
            metadata = {}
        
        # Normalize line endings (convert \r\n to \n)
        text = text.replace('\r\n', '\n')
        
        # Try to split by double newlines first (proper paragraphs)
        paragraphs = re.split(r'\n\n+', text)
        
        # If we only get 1 paragraph, split by single newlines
        if len(paragraphs) == 1:
            paragraphs = text.split('\n')
        
        chunks = []
        chunk_id = 0
        current_chunk = ""
        current_start = 0
        
        char_offset = 0
        
        for para in paragraphs:
            para = para.strip()
            
            if not para:
                char_offset += 2  # Account for newlines
                continue
            
            # If this paragraph alone exceeds max size, split it further
            if len(para) > self.max_chunk_size:
                # If we have accumulated text, save it first
                if current_chunk:
                    chunk = Chunk(
                        text=current_chunk,
                        start_idx=current_start,
                        end_idx=current_start + len(current_chunk),
                        chunk_id=chunk_id,
                        metadata={
                            **metadata,
                            'strategy': self.get_strategy_name(),
                            'method': 'structure',
                        }
                    )
                    chunks.append(chunk)
                    chunk_id += 1
                    current_chunk = ""
                
                # Split the large paragraph into sentences
                sentences = re.split(r'[.!?؟]+\s+', para)
                temp_chunk = ""
                
                for sentence in sentences:
                    if len(temp_chunk) + len(sentence) > self.max_chunk_size and temp_chunk:
                        # Save current temp chunk
                        chunk = Chunk(
                            text=temp_chunk,
                            start_idx=char_offset,
                            end_idx=char_offset + len(temp_chunk),
                            chunk_id=chunk_id,
                            metadata={
                                **metadata,
                                'strategy': self.get_strategy_name(),
                                'method': 'structure_sentence',
                            }
                        )
                        chunks.append(chunk)
                        chunk_id += 1
                        temp_chunk = sentence
                    else:
                        temp_chunk += (" " + sentence if temp_chunk else sentence)
                
                # Save remaining temp chunk
                if temp_chunk:
                    current_chunk = temp_chunk
                    current_start = char_offset
            
            # If adding this paragraph would exceed max size, create chunk
            elif len(current_chunk) + len(para) > self.max_chunk_size and current_chunk:
                # Always create chunk if we have content
                chunk = Chunk(
                    text=current_chunk,
                    start_idx=current_start,
                    end_idx=current_start + len(current_chunk),
                    chunk_id=chunk_id,
                    metadata={
                        **metadata,
                        'strategy': self.get_strategy_name(),
                        'method': 'structure',
                    }
                )
                chunks.append(chunk)
                chunk_id += 1
                
                # Start new chunk
                current_chunk = para
                current_start = char_offset
            else:
                # Add to current chunk
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
                    current_start = char_offset
            
            char_offset += len(para) + 2  # +2 for paragraph separator
        
        # Add final chunk (even if smaller than min_size)
        if current_chunk:
            chunk = Chunk(
                text=current_chunk,
                start_idx=current_start,
                end_idx=current_start + len(current_chunk),
                chunk_id=chunk_id,
                metadata={
                    **metadata,
                    'strategy': self.get_strategy_name(),
                    'method': 'structure',
                }
            )
            chunks.append(chunk)
        
        return chunks
    
    def chunk_by_similarity(self, text: str, metadata: Dict = None) -> List[Chunk]:
        """
        Chunk text based on semantic similarity using embeddings
        Groups similar sentences together
        
        Args:
            text: Text to chunk
            metadata: Optional metadata
            
        Returns:
            List of Chunk objects
        """
        if metadata is None:
            metadata = {}
        
        if self.model is None:
            raise ValueError("Embedding model not initialized. Set use_embeddings=True")
        
        # Split into sentences
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return []
        
        # Generate embeddings
        embeddings = self.model.encode(sentences)
        
        chunks = []
        chunk_id = 0
        current_chunk_sentences = [sentences[0]]
        current_start = 0
        
        # Group sentences based on similarity
        for i in range(1, len(sentences)):
            # Calculate similarity with current chunk
            prev_embedding = embeddings[i - 1]
            curr_embedding = embeddings[i]
            
            similarity = np.dot(prev_embedding, curr_embedding) / (
                np.linalg.norm(prev_embedding) * np.linalg.norm(curr_embedding)
            )
            
            current_text = ' '.join(current_chunk_sentences)
            
            # Start new chunk if similarity is low or size exceeded
            if (similarity < 0.5 or len(current_text) > self.max_chunk_size) and \
               len(current_text) >= self.min_chunk_size:
                
                chunk = Chunk(
                    text=current_text,
                    start_idx=current_start,
                    end_idx=current_start + len(current_text),
                    chunk_id=chunk_id,
                    metadata={
                        **metadata,
                        'strategy': self.get_strategy_name(),
                        'method': 'similarity',
                        'avg_similarity': similarity,
                    }
                )
                chunks.append(chunk)
                chunk_id += 1
                
                # Start new chunk
                current_chunk_sentences = [sentences[i]]
                current_start += len(current_text)
            else:
                current_chunk_sentences.append(sentences[i])
        
        # Add final chunk
        if current_chunk_sentences:
            current_text = ' '.join(current_chunk_sentences)
            if len(current_text) >= self.min_chunk_size:
                chunk = Chunk(
                    text=current_text,
                    start_idx=current_start,
                    end_idx=current_start + len(current_text),
                    chunk_id=chunk_id,
                    metadata={
                        **metadata,
                        'strategy': self.get_strategy_name(),
                        'method': 'similarity',
                    }
                )
                chunks.append(chunk)
        
        return chunks
    
    def chunk(self, text: str, metadata: Dict = None) -> List[Chunk]:
        """
        Chunk text using semantic/structural analysis
        
        Args:
            text: Text to chunk
            metadata: Optional metadata
            
        Returns:
            List of Chunk objects
        """
        # Use structure-based chunking by default
        # Can switch to similarity-based if embeddings are enabled
        if self.use_embeddings:
            logger.info("Using similarity-based semantic chunking")
            chunks = self.chunk_by_similarity(text, metadata)
        else:
            logger.info("Using structure-based semantic chunking")
            chunks = self.chunk_by_structure(text, metadata)
        
        logger.info(f"Created {len(chunks)} chunks using semantic strategy")
        return chunks
    
    def get_strategy_name(self) -> str:
        return "semantic"


class AutoChunker(ChunkingStrategy):
    """
    Auto-selector that analyzes document structure
    and chooses the best chunking strategy
    """
    
    def __init__(
        self,
        fixed_chunker: Optional[FixedSizeChunker] = None,
        semantic_chunker: Optional[SemanticChunker] = None
    ):
        """
        Initialize auto-selector chunker
        
        Args:
            fixed_chunker: Optional custom fixed chunker
            semantic_chunker: Optional custom semantic chunker
        """
        self.fixed_chunker = fixed_chunker or FixedSizeChunker()
        self.semantic_chunker = semantic_chunker or SemanticChunker()
    
    def analyze_structure(self, text: str) -> Dict[str, float]:
        """
        Analyze document structure to determine best chunking strategy
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with structure metrics
        """
        lines = text.split('\n')
        total_lines = len(lines)
        
        if total_lines == 0:
            return {'header_density': 0, 'avg_para_length': 0, 'paragraph_count': 0}
        
        # Detect headers
        header_indices = self.semantic_chunker.detect_headers(lines)
        header_density = len(header_indices) / total_lines
        
        # Analyze paragraphs
        paragraphs = re.split(r'\n\n+', text)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        avg_para_length = np.mean([len(p) for p in paragraphs]) if paragraphs else 0
        
        return {
            'header_density': header_density,
            'avg_para_length': avg_para_length,
            'paragraph_count': len(paragraphs),
            'total_lines': total_lines,
        }
    
    def select_strategy(self, text: str) -> Tuple[ChunkingStrategy, str]:
        """
        Automatically select the best chunking strategy
        
        Args:
            text: Text to analyze
            
        Returns:
            Tuple of (chosen_strategy, reason)
        """
        metrics = self.analyze_structure(text)
        
        # Decision logic
        header_density = metrics['header_density']
        avg_para_length = metrics['avg_para_length']
        para_count = metrics['paragraph_count']
        total_length = len(text)
        
        # Use fixed-size for very long documents with uniform content
        if total_length > 10000 and para_count < 5:
            return self.fixed_chunker, f"Long uniform content ({total_length} chars, {para_count} paragraphs)"
        
        # Use semantic chunking if document has clear structure
        if header_density > 0.05:  # More than 5% of lines are headers
            return self.semantic_chunker, f"High header density ({header_density:.2%})"
        
        # Use semantic chunking if paragraphs are well-defined
        if para_count > 5 and 300 < avg_para_length < 800:
            return self.semantic_chunker, f"Well-defined paragraphs ({para_count} paras, avg: {avg_para_length:.0f} chars)"
        
        # Use fixed-size for very long paragraphs (likely no structure)
        if avg_para_length > 1000:
            return self.fixed_chunker, f"Very long paragraphs (avg: {avg_para_length:.0f} chars)"
        
        # Use fixed-size for short uniform content
        if avg_para_length < 200 and para_count > 20:
            return self.fixed_chunker, f"Many short paragraphs ({para_count} paras, avg: {avg_para_length:.0f} chars)"
        
        # Default to semantic for structured content
        return self.semantic_chunker, "Default choice for structured content"
    
    def chunk(self, text: str, metadata: Dict = None) -> List[Chunk]:
        """
        Automatically select and apply best chunking strategy
        
        Args:
            text: Text to chunk
            metadata: Optional metadata
            
        Returns:
            List of Chunk objects
        """
        if metadata is None:
            metadata = {}
        
        # Select strategy
        strategy, reason = self.select_strategy(text)
        
        logger.info(f"Auto-selected {strategy.get_strategy_name()} strategy: {reason}")
        
        # Add auto-selection info to metadata
        metadata['auto_selected'] = True
        metadata['selection_reason'] = reason
        
        # Apply selected strategy
        return strategy.chunk(text, metadata)
    
    def get_strategy_name(self) -> str:
        return "auto"
