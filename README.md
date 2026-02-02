# 📄 DocuRAG Parser

AI-powered document parser designed for **Retrieval-Augmented Generation (RAG)** systems.
The system supports **PDF, DOCX, and TXT** documents with **full Arabic language and diacritics (tashkeel) support**.

---

## 🚀 Overview

DocuRAG Parser ingests documents, understands their content, applies **intelligent chunking**, and stores them in:

* a **Vector Database** for semantic retrieval
* a **SQL Database** for structured metadata queries

It is fully benchmarked and ready to integrate with Large Language Models (LLMs) as part of a RAG pipeline.

---

## ✨ Features

* 📄 **Multi-format document parsing** (PDF, DOCX, TXT)
* 🧠 **Content analysis & semantic understanding**
* ✂️ **Intelligent chunking**

  * Fixed chunking for uniform documents
  * Dynamic chunking for structured or mixed-content documents
* 🗃️ **Vector Database integration** (ChromaDB)
* 🗄️ **SQL Database integration** (SQLite)
* 🇸🇦 **Arabic language support**
* 🔤 **Arabic diacritics (harakat / tashkeel) handling**
* 📊 **Benchmark suite** for retrieval accuracy, chunk quality, and latency
* 🤖 **RAG-ready architecture**
* 🌐 **Interactive Streamlit demo**

---

## 🏗️ Architecture

```
Document
   ↓
Parser (PDF / DOCX / TXT)
   ↓
Content Analyzer
   ↓
Chunk Selector
   ├─ Fixed Chunker
   └─ Dynamic Chunker
   ↓
Embeddings (Sentence Transformers)
   ↓
Vector DB (Chroma)  ←→  SQL DB (Metadata)
   ↓
Retriever
   ↓
RAG Pipeline (LLM-ready)
```

---

## 🧰 Technologies Used

* **Python**
* **Streamlit** (Demo UI)
* **sentence-transformers** (Multilingual embeddings)
* **ChromaDB** (Vector database)
* **SQLite** (Relational storage)
* **PyPDF / python-docx** (Document parsing)

---

## 📊 Benchmark Results

Benchmark tests are implemented in `benchmark/` and include:

* **Keyword-based retrieval accuracy**
* **Chunk semantic quality**
* **Latency (performance)**

### Sample Results

| Metric                         | Value      |
| ------------------------------ | ---------- |
| Avg Keyword Retrieval Accuracy | **1.00**   |
| Avg Chunk Quality              | **1.00**   |
| Avg Latency                    | ~**0.13s** |

---

## ▶️ How to Run Locally

### 1️⃣ Install dependencies

```bash
pip install -r requirements.txt
```

### 2️⃣ Ingest a document

```bash
python -m app.main
```

### 3️⃣ Run benchmark

```bash
python benchmark/run_benchmark.py
```

### 4️⃣ Run the demo

```bash
streamlit run demo/streamlit_app.py
```

---

## 🌐 Live Demo

👉 **Streamlit App:**
[https://docurag-parser.streamlit.app](https://docurag-parser.streamlit.app)

The demo allows you to:

* Upload Arabic or English documents (PDF / DOCX / TXT)
* View chunking strategy and number of chunks
* Ask questions and see retrieved answers
* Test Arabic text with diacritics

---

## ❓ Questions & Assumptions

**Question:** Should advanced RAG techniques (Graph RAG / RAPTOR) be implemented?
**Assumption:** These were treated as optional recommendations, not mandatory requirements.

**Question:** Is direct LLM integration required at this stage?
**Assumption:** The system is designed to be **LLM-ready** without binding to a specific provider.

---

## 🔮 Future Improvements

* Integrate live LLMs (OpenAI / Ollama / HuggingFace)
* Hybrid retrieval (semantic + keyword-based)
* Hierarchical / RAPTOR-style chunking
* Graph-based document relationships (Graph RAG)
* Scalable vector storage (Qdrant / Pinecone)

---

## 👤 Author

**Emad Qudah**
📧 Email: qudahemad@yahoo.com