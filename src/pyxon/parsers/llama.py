# src.pyxon.parsers.llama

import asyncio
from pathlib import Path

from langchain_core.documents import Document
from llama_cloud import AsyncLlamaCloud

from src.config import Settings
from src.pyxon.parsers.base import BaseParser
from src.pyxon.parsers.txt import PyxonTxtParser


class PyxonLlamaParser(BaseParser):
    SUPPORTED_EXTENSIONS = [".doc", ".docx", ".pdf", ".txt"]

    def __init__(self, file_path: Path):
        super().__init__(file_path)

        self.client = AsyncLlamaCloud(api_key=Settings.LLAMAINDEX_API_KEY)

    def parse(self) -> Document:
        suffix = self._file_path.suffix.lower()

        if suffix == ".txt":
            parser = PyxonTxtParser(self._file_path)
            self._doc = parser.parse()
            return self._doc

        try:
            self._doc = asyncio.run(self._parse_async())
            self.get_chunker_type()
            return self._doc
        except Exception as e:
            raise RuntimeError(f"Failed to parse {self._file_path}: {e}")

    async def _parse_async(self) -> Document:
        file_obj = await self.client.files.create(
            file=str(self._file_path), purpose="parse"
        )

        result = await self.client.parsing.parse(
            file_id=file_obj.id,
            tier="agentic",  # Agentic tier includes image descriptions in markdown automatically
            version="latest",
            input_options={},
            output_options={
                "markdown": {
                    "tables": {"output_tables_as_markdown": True},
                },
            },
            processing_options={
                "ignore": {"ignore_diagonal_text": True},
            },
            expand=["markdown", "text"],
        )

        if result.markdown and result.markdown.pages:
            content = "\n\n".join(
                f"Page number: {i}\n-----\n{page.markdown}"
                for i, page in enumerate(result.markdown.pages, start=1)
            )
        else:
            content = ""

        metadata = {
            "source": str(self._file_path),
            "parser": "llama_cloud",
        }

        return Document(page_content=content, metadata=metadata)
