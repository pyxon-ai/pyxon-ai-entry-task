"""Document parser using Docling for PDF, DOCX, and TXT files."""

import os
from pathlib import Path
from typing import Dict, Optional, Tuple
from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend

from src.models.document import Document, DocumentType, DocumentMetadata
from src.utils.text_utils import detect_arabic, detect_diacritics


class DoclingParser:
    """Document parser using Docling library."""

    def __init__(self):
        """Initialize the document converter."""
        # Configure PDF pipeline options for better text extraction
        pdf_options = PdfPipelineOptions()
        pdf_options.do_ocr = True  # Enable OCR for scanned documents
        pdf_options.do_table_structure = True  # Extract table structures
        
        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: pdf_options,
            }
        )

    def parse_file(self, file_path: str) -> Document:
        """Parse a document file and return structured Document object."""
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Determine file type
        file_type = self._get_file_type(path.suffix)
        # Special handling for plain text: read directly
        if file_type == DocumentType.TXT:
            content = path.read_text(encoding="utf-8")
            metadata = DocumentMetadata(
                title=path.stem,
                word_count=len(content.split()),
            )
            metadata.has_arabic = detect_arabic(content)
            metadata.has_diacritics = detect_diacritics(content)
            metadata.language = "ar" if metadata.has_arabic else "en"
        else:
            # Convert document via Docling
            result = self.converter.convert(file_path)
            # Extract content and metadata
            content = result.document.export_to_markdown()
            # Extract metadata
            metadata = self._extract_metadata(result, content, path)
        
        # Create document object
        document = Document(
            id=self._generate_document_id(path),
            filename=path.name,
            file_type=file_type,
            content=content,
            metadata=metadata,
        )
        
        return document

    def _get_file_type(self, extension: str) -> DocumentType:
        """Map file extension to DocumentType."""
        ext_map = {
            ".pdf": DocumentType.PDF,
            ".docx": DocumentType.DOCX,
            ".doc": DocumentType.DOCX,
            ".txt": DocumentType.TXT,
        }
        return ext_map.get(extension.lower(), DocumentType.TXT)

    def _extract_metadata(
        self, result, content: str, path: Path
    ) -> DocumentMetadata:
        """Extract metadata from parsed document."""
        doc = result.document
        
        # Get basic metadata
        metadata = DocumentMetadata(
            title=doc.title or path.stem,
            author=doc.author,
            subject=doc.subject,
            keywords=doc.keywords or [],
            created_date=doc.creation_date,
            modified_date=doc.modification_date,
            page_count=len(doc.pages) if hasattr(doc, 'pages') else None,
            word_count=len(content.split()),
        )
        
        # Detect language
        metadata.has_arabic = detect_arabic(content)
        metadata.has_diacritics = detect_diacritics(content)
        metadata.language = "ar" if metadata.has_arabic else "en"
        
        return metadata

    def _generate_document_id(self, path: Path) -> str:
        """Generate unique document ID."""
        import hashlib
        file_hash = hashlib.md5(str(path.absolute()).encode()).hexdigest()[:16]
        return f"doc_{file_hash}"

    def parse_text(self, text: str, filename: str = "text.txt") -> Document:
        """Parse raw text content."""
        metadata = DocumentMetadata(
            title=filename,
            word_count=len(text.split()),
        )
        
        # Detect Arabic and diacritics
        metadata.has_arabic = detect_arabic(text)
        metadata.has_diacritics = detect_diacritics(text)
        metadata.language = "ar" if metadata.has_arabic else "en"
        
        import hashlib
        file_hash = hashlib.md5(text.encode()).hexdigest()[:16]
        
        return Document(
            id=f"doc_{file_hash}",
            filename=filename,
            file_type=DocumentType.TXT,
            content=text,
            metadata=metadata,
        )
