"""Setup script for Pyxon AI Document Parser."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="pyxon-ai-document-parser",
    version="1.0.0",
    author="Pyxon AI",
    description="AI-powered document parser with full Arabic support",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.12",
    install_requires=[
        "python-dotenv>=1.0.0",
        "pydantic>=2.5.3",
        "pydantic-settings>=2.1.0",
        "docling>=2.0.0",
        "python-docx>=1.1.0",
        "PyPDF2>=3.0.1",
        "llama-index>=0.10.11",
        "sentence-transformers>=2.3.1",
        "FlagEmbedding>=1.2.10",
        "psycopg2-binary>=2.9.9",
        "pgvector>=0.2.5",
        "sqlalchemy>=2.0.25",
        "alembic>=1.13.1",
        "camel-tools>=1.5.2",
        "farasa>=0.1.5",
        "openai>=1.10.0",
        "anthropic>=0.18.1",
        "ragas>=0.1.7",
        "evaluate>=0.4.1",
        "fastapi>=0.109.0",
        "uvicorn>=0.27.0",
        "python-multipart>=0.0.6",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.4",
            "pytest-asyncio>=0.23.3",
            "pytest-cov>=4.1.0",
        ],
    },
)
