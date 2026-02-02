from .base_parser import BaseParser


class TXTParser(BaseParser):
    def parse(self, file_path: str):
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()

        return {
            "text": text,
            "source": file_path,
            "file_type": "txt"
        }