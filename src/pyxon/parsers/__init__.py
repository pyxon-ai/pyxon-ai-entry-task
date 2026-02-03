from pathlib import Path

from langchain_core.documents import Document

from src.pyxon.parsers.docx import PyxonDocxParser
from src.pyxon.parsers.llama import PyxonLlamaParser
from src.pyxon.parsers.pdf import PyxonPDFParser
from src.pyxon.parsers.txt import PyxonTxtParser

_REGISTRY: dict[str, type] = {}

for parser_cls in [PyxonPDFParser, PyxonDocxParser, PyxonTxtParser]:
    for ext in parser_cls.SUPPORTED_EXTENSIONS:
        _REGISTRY[ext] = parser_cls


def parse_document(file_path: str | Path, advanced=True) -> Document:
    path = Path(file_path)

    if advanced:
        parser = PyxonLlamaParser(path)
        doc = parser.parse()
        parser.get_chunker_type()

        return doc

    ext = path.suffix.lower()

    if ext not in _REGISTRY:
        raise ValueError(
            f"Unsupported file type: '{ext}'. Supported: {list(_REGISTRY.keys())}"
        )

    parser = _REGISTRY[ext](file_path=path)

    doc = parser.parse()
    parser.get_chunker_type()

    return doc
