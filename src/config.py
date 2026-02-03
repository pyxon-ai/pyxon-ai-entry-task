import os
from dataclasses import dataclass
from pathlib import Path

try:
    import streamlit as st
    _has_streamlit = True
except ImportError:
    _has_streamlit = False


def _get_secret(key: str, default: str = None) -> str:
    if _has_streamlit and key in st.secrets:
        return st.secrets[key]
    return default


@dataclass
class Settings:
    DATA: Path = Path(__file__).parent.parent / "data"
    TESTS = DATA / 'tests'
    TESTSET = TESTS / 'testset.csv'
    
    PARAGRAPH_VARIATION_THRESH: float = 0.2
    INDEX: str = "pyxon"

    EMBEDDING_MODEL_NAME: str = "text-embedding-3-large"
    CROSS_ENCODER_MODEL_NAME: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    LLM_MODEL_NAME: str = "llama-3.3-70b-versatile"
    TEST_MODEL: str = "gpt-4o-mini"

    DIMENSIONS: int = 1024
    CHUNK_OVERLAP: float = 0.2
    
    PINECONE_API_KEY: str = _get_secret("PINECONE_API_KEY")
    OPENAI_API_KEY: str = _get_secret("OPENAI_API_KEY")
    DATABASE_URL: str = _get_secret("DATABASE_URL")
    LLAMAINDEX_API_KEY: str = _get_secret("LLAMAINDEX_API_KEY")
    LANGSMITH_API_KEY: str = _get_secret("LANGSMITH_API_KEY")
    GROQ_API_KEY: str = _get_secret("GROQ_API_KEY")

    PERCENTILE_THRESH: float = 0.9
    TOP_K: int = 5
    SIMILARITY_THRESHOLD: float = 0.8
    MAX_RAG_ITERATIONS: int = 6

    TESTSET_SIZE: int = 10