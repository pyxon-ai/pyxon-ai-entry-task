"""Chunking strategies for document processing."""

import re
from typing import List, Optional
from enum import Enum

from src.models.document import Document, Chunk, ChunkMetadata, ChunkingStrategy
from src.utils.text_utils import estimate_tokens, detect_arabic, detect_diacritics


class ChunkStrategy(Enum):
    """Chunking strategy types."""
    FIXED = "fixed"
    DYNAMIC = "dynamic"
    SEMANTIC = "semantic"
    HIERARCHICAL = "hierarchical"


class FixedChunker:
    """Fixed-size chunking strategy."""

    def __init__(self, chunk_size: int = 512, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, document: Document) -> List[Chunk]:
        """Split document into fixed-size chunks."""
        chunks = []
        content = document.content
        
        # Split into paragraphs first to avoid breaking sentences
        paragraphs = re.split(r'\n\s*\n', content)
        
        current_chunk = ""
        chunk_index = 0
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            # Check if adding paragraph exceeds chunk size
            if len(current_chunk) + len(paragraph) + 2 > self.chunk_size:
                if current_chunk:
                    chunks.append(self._create_chunk(
                        document, current_chunk, chunk_index
                    ))
                    chunk_index += 1
                    
                    # Add overlap from previous chunk
                    if self.overlap > 0:
                        words = current_chunk.split()
                        overlap_text = ' '.join(words[-self.overlap:])
                        current_chunk = overlap_text + "\n\n" + paragraph
                    else:
                        current_chunk = paragraph
                else:
                    current_chunk = paragraph
            else:
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
        
        # Add remaining content
        if current_chunk:
            chunks.append(self._create_chunk(document, current_chunk, chunk_index))
        
        return chunks

    def _create_chunk(
        self, document: Document, content: str, chunk_index: int
    ) -> Chunk:
        """Create a Chunk object."""
        import uuid
        
        return Chunk(
            id=str(uuid.uuid4()),
            document_id=document.id,
            content=content,
            metadata=ChunkMetadata(
                chunk_index=chunk_index,
                token_count=estimate_tokens(content),
                char_count=len(content),
                has_arabic=detect_arabic(content),
                has_diacritics=detect_diacritics(content),
            ),
        )


class DynamicChunker:
    """Dynamic chunking based on document structure."""

    def __init__(self, max_chunk_size: int = 1000, min_chunk_size: int = 200):
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size

    def chunk(self, document: Document) -> List[Chunk]:
        """Split document based on structure (headings, paragraphs, etc.)."""
        chunks = []
        content = document.content
        
        # Parse markdown structure
        sections = self._parse_markdown_structure(content)
        
        chunk_index = 0
        current_section = []
        current_size = 0
        current_heading = None
        
        for section in sections:
            section_type = section['type']
            section_content = section['content']
            section_size = len(section_content)
            
            # Update heading if this is a heading
            if section_type == 'heading':
                current_heading = section_content
            
            # Check if adding this section would exceed max size
            if current_size + section_size > self.max_chunk_size:
                if current_section:
                    # Create chunk from accumulated sections
                    chunk_content = '\n\n'.join(current_section)
                    chunks.append(self._create_chunk(
                        document, chunk_content, chunk_index, current_heading
                    ))
                    chunk_index += 1
                    
                    # Start new section
                    current_section = [section_content]
                    current_size = section_size
                    current_heading = section_type == 'heading' and section_content or None
                else:
                    # Single section exceeds max size, split it
                    sub_chunks = self._split_large_section(
                        document, section_content, chunk_index, current_heading
                    )
                    chunks.extend(sub_chunks)
                    chunk_index += len(sub_chunks)
                    current_section = []
                    current_size = 0
            else:
                current_section.append(section_content)
                current_size += section_size
        
        # Add remaining content
        if current_section:
            chunk_content = '\n\n'.join(current_section)
            chunks.append(self._create_chunk(
                document, chunk_content, chunk_index, current_heading
            ))
        
        return chunks

    def _parse_markdown_structure(self, content: str) -> List[dict]:
        """Parse markdown content into structured sections."""
        sections = []
        lines = content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # Check for headings
            if line.startswith('#'):
                level = len(line) - len(line.lstrip('#'))
                # Preserve original markdown line so tests can see '# Heading'
                sections.append({
                    'type': 'heading',
                    'content': line.strip(),
                    'level': level,
                })
            # Check for tables
            elif '|' in line:
                # Collect table rows
                table_lines = []
                while i < len(lines) and '|' in lines[i]:
                    table_lines.append(lines[i])
                    i += 1
                sections.append({
                    'type': 'table',
                    'content': '\n'.join(table_lines),
                })
                continue
            # Regular paragraph
            elif line.strip():
                # Collect paragraph lines
                paragraph_lines = []
                while i < len(lines) and lines[i].strip() and not lines[i].startswith('#'):
                    paragraph_lines.append(lines[i])
                    i += 1
                sections.append({
                    'type': 'paragraph',
                    'content': ' '.join(paragraph_lines).strip(),
                })
                continue
            
            i += 1
        
        return sections

    def _split_large_section(
        self, document: Document, content: str, chunk_index: int, heading: Optional[str]
    ) -> List[Chunk]:
        """Split a large section into smaller chunks."""
        chunks = []
        sentences = re.split(r'[.!?؟]+', content)
        
        current_chunk = ""
        current_idx = chunk_index
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            if len(current_chunk) + len(sentence) + 2 > self.max_chunk_size:
                if current_chunk:
                    chunks.append(self._create_chunk(
                        document, current_chunk, current_idx, heading
                    ))
                    current_idx += 1
                    current_chunk = sentence
                else:
                    current_chunk = sentence
            else:
                if current_chunk:
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence
        
        if current_chunk:
            chunks.append(self._create_chunk(
                document, current_chunk, current_idx, heading
            ))
        
        return chunks

    def _create_chunk(
        self, document: Document, content: str, chunk_index: int, heading: Optional[str]
    ) -> Chunk:
        """Create a Chunk object."""
        import uuid
        
        return Chunk(
            id=str(uuid.uuid4()),
            document_id=document.id,
            content=content,
            metadata=ChunkMetadata(
                chunk_index=chunk_index,
                chunk_type="section",
                heading=heading,
                token_count=estimate_tokens(content),
                char_count=len(content),
                has_arabic=detect_arabic(content),
                has_diacritics=detect_diacritics(content),
            ),
        )


class IntelligentChunker:
    """Intelligent chunking that selects the best strategy."""

    def __init__(self, fixed_chunker: FixedChunker, dynamic_chunker: DynamicChunker):
        self.fixed_chunker = fixed_chunker
        self.dynamic_chunker = dynamic_chunker

    def analyze_document(self, document: Document) -> ChunkingStrategy:
        """
        Analyze document and determine best chunking strategy.
        
        Returns:
            ChunkingStrategy to use
        """
        content = document.content
        
        # Check for markdown structure
        has_headings = bool(re.search(r'^#{1,6}\s', content, re.MULTILINE))
        has_tables = '|' in content
        has_lists = bool(re.search(r'^\s*[-*+]\s', content, re.MULTILINE))
        
        # Check document structure
        has_structure = has_headings or has_tables or has_lists
        
        # Check document length
        is_long_document = len(content) > 10000
        
        # Check content uniformity
        paragraphs = re.split(r'\n\s*\n', content)
        avg_paragraph_length = sum(len(p) for p in paragraphs) / len(paragraphs) if paragraphs else 0
        
        # Decision logic
        if has_structure and is_long_document:
            return ChunkingStrategy.DYNAMIC
        elif has_structure:
            return ChunkingStrategy.DYNAMIC
        elif avg_paragraph_length > 500:
            return ChunkingStrategy.FIXED
        else:
            return ChunkingStrategy.FIXED

    def chunk(self, document: Document) -> List[Chunk]:
        """Chunk document using the best strategy."""
        strategy = self.analyze_document(document)
        document.chunking_strategy = strategy
        
        if strategy == ChunkingStrategy.DYNAMIC:
            return self.dynamic_chunker.chunk(document)
        else:
            return self.fixed_chunker.chunk(document)
