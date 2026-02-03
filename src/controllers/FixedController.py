from .BaseController import BaseController
import os
from langchain_community.document_loaders import TextLoader
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_community.document_loaders import Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from models.enums.ProcessingEnum import ProcessingEnum


class FixedController(BaseController):

    def __init__(self):
        super().__init__()

    def get_file_extension(self, file_path: str):
        return os.path.splitext(file_path)[-1]

    def get_file_loader(self, file_path: str):
        file_ext = self.get_file_extension(file_path=file_path)

        if file_ext == ProcessingEnum.TXT.value:
            return TextLoader(file_path, encoding="utf-8")

        if file_ext == ProcessingEnum.PDF.value:
            return PyMuPDFLoader(file_path)
        
        if file_ext == ProcessingEnum.DOCX.value:
            return Docx2txtLoader(file_path)
        
        return None

    def get_file_content(self, file_path: str):
        loader = self.get_file_loader(file_path=file_path)
        return loader.load()

    def process_file_content(self, file_content: list,
                            chunk_size: int=100, overlap_size: int=20):
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap_size,
            length_function=len,
        )

        file_content_texts = [rec.page_content for rec in file_content]
        file_content_metadata = [rec.metadata for rec in file_content]

        chunks = text_splitter.create_documents(
            file_content_texts,
            metadatas=file_content_metadata
        )

        return chunks
