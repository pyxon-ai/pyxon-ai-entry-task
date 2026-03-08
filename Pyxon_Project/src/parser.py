import os
import re
import fitz  # PyMuPDF
from docx import Document

class DocumentParser:
    """
    A simple, modular parser for extracting text from PDF, DOCX, and TXT files.
    Ensures UTF-8 encoding and supports Arabic text (RTL and diacritics) effectively.
    """

    def __init__(self):
        pass

    def parse(self, file_path: str) -> str:
        """
        Reads a document and returns its full text content.
        Dynamically chooses the extraction method based on the file extension.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()

        if ext == '.txt':
            return self._parse_txt(file_path)
        elif ext == '.docx':
            return self._parse_docx(file_path)
        elif ext == '.pdf':
            return self._parse_pdf(file_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}. Supported formats are .txt, .docx, .pdf")

    def _parse_txt(self, file_path: str) -> str:
        """Extract text from a TXT file ensuring UTF-8 encoding."""
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()

    def _parse_docx(self, file_path: str) -> str:
        """Extract text from a DOCX file."""
        doc = Document(file_path)
        full_text = []
        for para in doc.paragraphs:
            # We preserve paragraph breaks
            if para.text.strip():
                full_text.append(para.text)
        return '\\n'.join(full_text)

    def _parse_pdf(self, file_path: str) -> str:
        """
        Extract text from a PDF file.
        PyMuPDF handles Arabic text and diacritics quite well naturally.
        """
        text_content = []
        with fitz.open(file_path) as pdf_doc:
            for page_num in range(len(pdf_doc)):
                page = pdf_doc.load_page(page_num)
                # extract_text automatically handles standard RTL if text blocks are encoded correctly.
                text = page.get_text("text") 
                if text.strip():
                    text_content.append(text)
                    
        full_text = '\\n\\n'.join(text_content)
        
        # Clean up PDF artifacts: 
        # Convert single newlines to spaces so they don't break sentences in half,
        # but keep double newlines which indicate true paragraph breaks.
        full_text = re.sub(r'(?<!\\n)\\n(?!\\n)', ' ', full_text)
        return full_text

# Quick demonstration/test (can be removed or left as module test)
if __name__ == "__main__":
    parser = DocumentParser()
    print("Parser initialized successfully. Ready to process files.")
