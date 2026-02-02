# Pyxon AI – Junior Engineer Entry Task

## Overview

This project implements an **AI-powered document parser** that intelligently processes documents, understands their content, and prepares them for retrieval-augmented generation (RAG) systems. The parser supports multiple file formats, intelligent chunking strategies, and full Arabic language support including diacritics (harakat).

---

## Task Requirements

### 1. Document Parser

The parser supports:

- **Multiple file formats**
  - PDF
  - DOC/DOCX
  - TXT

- **Content Understanding**
  - Semantic analysis of documents
  - Detection of structure, topics, and key concepts
  - Automatic selection of the most suitable chunking strategy

- **Intelligent Chunking**
  - **Fixed chunking** for uniform or structured documents
  - **Dynamic chunking** for documents with varying structure (e.g., chapters, mixed content)
  - Strategy selection is based on document analysis heuristics

- **Storage**
  - Vector Database for semantic retrieval
  - SQL Database for metadata and structured queries

- **Arabic Language Support**
  - Full Arabic text support
  - Preservation of Arabic diacritics (harakat / tashkeel)
  - Proper UTF-8 encoding and RTL handling

---

### 2. Benchmark Suite

The benchmark suite evaluates:

- Retrieval accuracy (Recall@k, MRR)
- Chunk semantic coherence
- Performance (ingest and retrieval latency, memory)
- Arabic-specific tests (with and without diacritics)

---

### 3. RAG Integration

The system is RAG-ready and designed to:

- Retrieve relevant chunks using vector similarity
- Apply structured filtering via SQL
- Support advanced RAG extensions such as Graph RAG and RAPTOR

---

## Technical Specifications

### Advanced RAG Techniques

This implementation includes:

- **Graph RAG**
  - Entity-aware retrieval using a lightweight knowledge graph
  - Improves multi-hop and context-aware retrieval

- **RAPTOR**
  - Hierarchical chunk summarization and tree-based retrieval

- **Hybrid Retrieval**
  - Vector-based semantic retrieval with metadata filtering

---

### Technology Stack

- **Language:** Python 3.10+
- **Document Processing:** pypdf, python-docx
- **Embeddings:** Multilingual sentence-transformers (Arabic-safe)
- **Vector DB:** Chroma
- **SQL DB:** SQLite
- **Orchestration:** LangGraph
- **Demo:** Streamlit

---

## Implementation (How to Run)

This repository uses **LangGraph** to orchestrate two main pipelines:

- **Ingest Graph:** extract → analyze → chunk → embed → store
- **RAG Graph:** query → retrieve → (optional Graph RAG / RAPTOR) → response

> **Note:** Only text-based PDFs are supported. OCR is out of scope.

---

### Installation

```bash
pip install -r requirements.txt
```
