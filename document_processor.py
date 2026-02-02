
import os
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai import OpenAIEmbeddings

class DocumentProcessor:
    def __init__(self):
        # Using OpenAI embeddings to understand semantic meaning of sentences
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        
        # Configure the semantic chunker – it splits text based on topic changes
        self.splitter = SemanticChunker(
            self.embeddings,
            breakpoint_threshold_type="percentile"
        )

    def load_and_split(self, file_path):
        ext = os.path.splitext(file_path)[-1].lower()
        full_text = ""

        # Extract text based on file type
        if ext == ".pdf":
            loader = PyPDFLoader(file_path)
            pages = loader.load()
            full_text = " ".join([p.page_content for p in pages])
        elif ext in [".docx", ".doc"]:
            loader = Docx2txtLoader(file_path)
            pages = loader.load()
            full_text = " ".join([p.page_content for p in pages])
        elif ext == ".txt":
            with open(file_path, "r", encoding="utf-8") as f:
                full_text = f.read()
        else:
            raise ValueError(f"Unsupported file format: {ext}")

        if not full_text.strip():
            return []

        # The system analyzes sentences and splits them when context changes
        chunks = self.splitter.create_documents([full_text])
        
        for chunk in chunks:
            chunk.metadata = {"source": os.path.basename(file_path)}
            
        return chunks
    

    

## Another Way

# import os
# from dotenv import load_dotenv
# from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
# from langchain_text_splitters import RecursiveCharacterTextSplitter
# from langchain_openai import OpenAIEmbeddings

# load_dotenv()

# class DocumentProcessor:
#     def __init__(self):
#         # Using OpenAI embedding models for strong Arabic language support
#         self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        
#         # Smart text splitting: Arabic punctuation is used as separators
#         # to avoid breaking semantic meaning
#         self.text_splitter = RecursiveCharacterTextSplitter(
#             chunk_size=1000,
#             chunk_overlap=100,
#             separators=["\n\n", "\n", ".", "؟", "!", "،", " ", ""]
#         )

#     def load_and_split(self, file_path):
#         ext = os.path.splitext(file_path)[-1].lower()
        
#         if ext == '.pdf':
#             loader = PyPDFLoader(file_path)
#         elif ext in ['.doc', '.docx']:
#             loader = Docx2txtLoader(file_path)
#         elif ext == '.txt':
#             loader = TextLoader(file_path, encoding='utf-8')
#         else:
#             raise ValueError(f"Unsupported file type: {ext}")

#         documents = loader.load()
#         chunks = self.text_splitter.split_documents(documents)
        
#         return chunks

    
    