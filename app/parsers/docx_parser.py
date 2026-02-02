from docx import Document
from .base_parser import BaseParser


class DOCXParser(BaseParser):
    def parse(self, file_path: str):
        doc = Document(file_path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]

        full_text = "\n".join(paragraphs)

        return {
            "text": full_text,
            "source": file_path,
            "file_type": "docx"
        }