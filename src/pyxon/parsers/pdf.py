# src.pyxon.parsers.pdf

from langchain_core.documents import Document
from pypdf import PdfReader

from src.pyxon.parsers.base import BaseParser


class PyxonPDFParser(BaseParser):
    SUPPORTED_EXTENSIONS: list[str] = [".pdf"]

    def __init__(self, file_path):
        super().__init__(file_path)

    def parse(self) -> Document:
        pdf_reader = PdfReader(self._file_path)

        pages = [page.extract_text() for page in pdf_reader.pages]

        self._doc = Document(
            page_content="\n".join(pages),
            metadata={"source": str(self._file_path), "parser": "pypdf"},
        )

        return self._doc
