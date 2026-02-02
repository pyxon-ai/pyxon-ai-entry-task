"""
Intelligent Chunking Service
Implements both fixed-size and dynamic chunking strategies
"""

import re
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from loguru import logger
import nltk

# Download required NLTK data (run once)
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)


@dataclass
class Chunk:
    """Represents a text chunk"""
    text: str
    index: int
    start_char: int
    end_char: int
    metadata: Dict[str, Any]


class ChunkingService:
    """Intelligent text chunking with strategy selection"""
    
    def __init__(self, default_chunk_size: int = 512, default_overlap: int = 50):
        self.default_chunk_size = default_chunk_size
        self.default_overlap = default_overlap
    
    def decide_strategy(self, text: str, metadata: Dict[str, Any]) -> str:
        """
        Intelligently decide which chunking strategy to use
        
        Decision factors:
        - Document structure (headings, paragraphs)
        - Content complexity
        - Document length
        - Language (Arabic vs English)
        
        Args:
            text: Document text
            metadata: Document metadata
            
        Returns:
            'fixed' or 'dynamic'
        """
        # Calculate complexity score
        complexity_score = self._calculate_complexity(text)
        
        # Check for structural elements
        has_structure = self._has_structural_elements(text)
        
        # Language consideration
        language = metadata.get('language', 'unknown')
        
        logger.info(f"Complexity score: {complexity_score}, Has structure: {has_structure}, Language: {language}")
        
        # Decision logic
        if complexity_score > 0.6 or has_structure:
            return 'dynamic'
        else:
            return 'fixed'
    
    def chunk_text(self, text: str, strategy: str = 'auto', metadata: Dict[str, Any] = None) -> List[Chunk]:
        """
        Chunk text using specified strategy
        
        Args:
            text: Text to chunk
            strategy: 'fixed', 'dynamic', or 'auto'
            metadata: Document metadata
            
        Returns:
            List of Chunk objects
        """
        if metadata is None:
            metadata = {}
        
        # Auto-select strategy if needed
        if strategy == 'auto':
            strategy = self.decide_strategy(text, metadata)
        
        logger.info(f"Using {strategy} chunking strategy")
        
        if strategy == 'fixed':
            chunks = self.fixed_chunking(text)
        elif strategy == 'dynamic':
            chunks = self.dynamic_chunking(text)
        else:
            raise ValueError(f"Unknown strategy: {strategy}")
        
        return chunks
    
    def fixed_chunking(self, text: str) -> List[Chunk]:
        """
        Fixed-size chunking with overlap
        
        Args:
            text: Text to chunk
            
        Returns:
            List of Chunk objects
        """
        chunks = []
        words = text.split()
        
        if not words:
            return chunks
        
        chunk_size = self.default_chunk_size
        overlap = self.default_overlap
        
        start_idx = 0
        chunk_index = 0
        
        while start_idx < len(words):
            # Get chunk words
            end_idx = min(start_idx + chunk_size, len(words))
            chunk_words = words[start_idx:end_idx]
            chunk_text = ' '.join(chunk_words)
            
            # Calculate character positions (approximate)
            start_char = len(' '.join(words[:start_idx]))
            end_char = start_char + len(chunk_text)
            
            # Create chunk
            chunk = Chunk(
                text=chunk_text,
                index=chunk_index,
                start_char=start_char,
                end_char=end_char,
                metadata={
                    'strategy': 'fixed',
                    'word_count': len(chunk_words),
                    'char_count': len(chunk_text)
                }
            )
            
            chunks.append(chunk)
            
            # Move to next chunk with overlap
            start_idx += (chunk_size - overlap)
            chunk_index += 1
        
        logger.info(f"Created {len(chunks)} fixed-size chunks")
        return chunks
    
    def dynamic_chunking(self, text: str) -> List[Chunk]:
        """
        Dynamic/semantic chunking based on document structure
        
        Uses:
        - Paragraph boundaries
        - Sentence boundaries
        - Semantic similarity (simplified)
        
        Args:
            text: Text to chunk
            
        Returns:
            List of Chunk objects
        """
        chunks = []
        
        # Split by paragraphs first
        paragraphs = self._split_paragraphs(text)
        
        chunk_index = 0
        current_position = 0
        
        for para in paragraphs:
            if not para.strip():
                continue
            
            # If paragraph is too large, split by sentences
            if len(para.split()) > self.default_chunk_size:
                sentences = self._split_sentences(para)
                current_chunk = []
                current_size = 0
                
                for sentence in sentences:
                    sentence_size = len(sentence.split())
                    
                    if current_size + sentence_size > self.default_chunk_size and current_chunk:
                        # Create chunk from accumulated sentences
                        chunk_text = ' '.join(current_chunk)
                        chunk = Chunk(
                            text=chunk_text,
                            index=chunk_index,
                            start_char=current_position,
                            end_char=current_position + len(chunk_text),
                            metadata={
                                'strategy': 'dynamic',
                                'type': 'multi-sentence',
                                'sentence_count': len(current_chunk),
                                'word_count': current_size
                            }
                        )
                        chunks.append(chunk)
                        chunk_index += 1
                        current_position += len(chunk_text) + 1
                        
                        current_chunk = []
                        current_size = 0
                    
                    current_chunk.append(sentence)
                    current_size += sentence_size
                
                # Add remaining sentences
                if current_chunk:
                    chunk_text = ' '.join(current_chunk)
                    chunk = Chunk(
                        text=chunk_text,
                        index=chunk_index,
                        start_char=current_position,
                        end_char=current_position + len(chunk_text),
                        metadata={
                            'strategy': 'dynamic',
                            'type': 'multi-sentence',
                            'sentence_count': len(current_chunk),
                            'word_count': current_size
                        }
                    )
                    chunks.append(chunk)
                    chunk_index += 1
                    current_position += len(chunk_text) + 1
            else:
                # Paragraph is small enough, use as single chunk
                chunk = Chunk(
                    text=para,
                    index=chunk_index,
                    start_char=current_position,
                    end_char=current_position + len(para),
                    metadata={
                        'strategy': 'dynamic',
                        'type': 'paragraph',
                        'word_count': len(para.split())
                    }
                )
                chunks.append(chunk)
                chunk_index += 1
                current_position += len(para) + 1
        
        logger.info(f"Created {len(chunks)} dynamic chunks")
        return chunks
    
    def _calculate_complexity(self, text: str) -> float:
        """
        Calculate text complexity score (0-1)
        
        Factors:
        - Average sentence length
        - Vocabulary diversity
        - Presence of special characters
        
        Args:
            text: Input text
            
        Returns:
            Complexity score between 0 and 1
        """
        sentences = self._split_sentences(text)
        
        if not sentences:
            return 0.0
        
        # Average sentence length
        avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)
        length_score = min(avg_sentence_length / 30, 1.0)  # Normalize to 0-1
        
        # Vocabulary diversity (unique words / total words)
        words = text.lower().split()
        if words:
            diversity_score = len(set(words)) / len(words)
        else:
            diversity_score = 0.0
        
        # Combine scores
        complexity = (length_score + diversity_score) / 2
        
        return complexity
    
    def _has_structural_elements(self, text: str) -> bool:
        """
        Check if text has structural elements (headings, lists, etc.)
        
        Args:
            text: Input text
            
        Returns:
            True if structural elements are found
        """
        # Check for headings (lines with fewer words, possibly all caps)
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Potential heading: short line (< 10 words)
            if len(line.split()) < 10:
                # Check if it's all caps or ends with colon
                if line.isupper() or line.endswith(':'):
                    return True
        
        # Check for bullet points or numbered lists
        list_pattern = re.compile(r'^\s*[\-\*\•\d]+[\.\)]\s+')
        for line in lines:
            if list_pattern.match(line):
                return True
        
        return False
    
    def _split_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs"""
        # Split by double newlines or more
        paragraphs = re.split(r'\n\s*\n', text)
        return [p.strip() for p in paragraphs if p.strip()]
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences using NLTK"""
        try:
            sentences = nltk.sent_tokenize(text)
            return [s.strip() for s in sentences if s.strip()]
        except Exception as e:
            logger.warning(f"NLTK sentence tokenization failed: {e}, using fallback")
            # Fallback: simple split by period
            sentences = re.split(r'[.!?]+', text)
            return [s.strip() for s in sentences if s.strip()]
