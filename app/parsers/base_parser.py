from abc import ABC, abstractmethod
from typing import Dict


class BaseParser(ABC):
    """
    Base class for all document parsers.
    Each parser should return raw text without modifying content
    (especially important for Arabic diacritics).
    """

    @abstractmethod
    def parse(self, file_path: str) -> Dict:
        """
        Parse a document and return its content and metadata.

        Returns:
            {
                "text": str,
                "source": str,
                "file_type": str
            }
        """
        pass
