from pypdf import PdfReader
from .base_parser import BaseParser
import re


class PDFParser:
    def parse(self, file_path: str) -> str:
        reader = PdfReader(file_path)
        raw_text = ""

        for page in reader.pages:
            text = page.extract_text()
            if text:
                raw_text += text + "\n"

        return self._clean_arabic_text(raw_text)

    def _clean_arabic_text(self, text: str) -> str:
        lines = [l.strip() for l in text.split("\n")]

        lines = [l for l in lines if len(l) > 20]

        lines = [re.sub(r"\s+", " ", l) for l in lines]

        return "\n\n".join(lines)
