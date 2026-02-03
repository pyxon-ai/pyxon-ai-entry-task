# src.pyxon.parsers.base

from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np
from langchain_core.documents import Document

from src.config import Settings


class BaseParser(ABC):
    SUPPORTED_EXTENSIONS: list[str] = []

    def __init__(self, file_path: Path):
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if file_path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"{self.__class__.__name__} does not support "
                f"'{file_path.suffix}'. Supported: {self.SUPPORTED_EXTENSIONS}"
            )

        self._file_path = file_path
        self._doc = Document(page_content="")

        super().__init__()

    @abstractmethod
    def parse(self) -> Document:
        pass

    def get_chunker_type(self):
        paragraphs = self._doc.page_content.split("\n")

        paragraphs_len = np.array([len(p) for p in paragraphs])

        std = paragraphs_len.std()
        mean = paragraphs_len.mean()

        self._doc.metadata["chunk_size"] = int(mean)
        self._doc.metadata["chunk_overlap"] = int(mean * Settings.CHUNK_OVERLAP)

        if mean == 0 or len(paragraphs) <= 1:
            self._doc.metadata["chunking_strategy"] = "FIXED"
            return "FIXED"

        cv = std / mean

        if cv < Settings.PARAGRAPH_VARIATION_THRESH:
            self._doc.metadata["chunking_strategy"] = "FIXED"
            return "FIXED"
        else:
            self._doc.metadata["chunking_strategy"] = "DYNAMIC"
            return "DYNAMIC"
