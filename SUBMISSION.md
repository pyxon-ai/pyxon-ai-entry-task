


## Summary

This implementation delivers a modular Retrieval-Augmented Generation (RAG) pipeline optimized for high-performance Arabic document processing.
The system features intelligent chunking based on document structure, advanced Arabic normalization (visual glyph correction + diacritics preservation), and a hybrid storage architecture (Vector + SQL).

---

## Contact Information

📧 Email: abdullahikhmaies@gmail.com
📱 Phone: +962 788 735 225

---

## Demo Link

🔗 [Check the live video demo here](https://your-demo-link.com)

> The demo showcases the upload of complex Arabic PDFs, real-time preview usage, and semantic search retrieval.

---
# 🚀 RAG System Implementation 
        ┌──────────────┐
        │  Documents   │
        │ PDF/DOCX/TXT │
        └──────┬───────┘
               ↓
    ┌────────────────────┐
    │ Document Loader     │
    │ (PyMuPDF / docx)   │
    └──────┬─────────────┘
           ↓
    ┌────────────────────┐
    │ Content Analyzer   │
    │ - Language detect  │
    │ - Structure detect │
    │ - Preprocessing    │
    └──────┬─────────────┘
           ↓
    ┌────────────────────┐
    │ Chunking Engine    │
    │ - Fixed            │
    │ - Dynamic (Header) │
    │ - Sentence-Aware   │
    └──────┬─────────────┘
           ↓
 ┌───────────────┬─────────────────┐
 ↓               ↓                 ↓
┌───────────┐  ┌─────────────┐  ┌──────────────┐
│ Vector DB │  │ SQL DB      │  │ Benchmarks   │
│ (Chroma)  │  │ (SQLite)    │  │ (Metrics)    │
└───────────┘  └─────────────┘  └──────────────┘
     ↓
┌────────────────────┐
│ RAG Retrieval API  │
│ (FastAPI)          │
└────────────────────┘

## Features Implemented

* [x] Document parsing (PDF via PyMuPDF, DOCX, TXT)
* [x] Content analysis and chunking strategy selection
* [x] Fixed and Dynamic (Heading-based) chunking
* [x] Vector DB integration (ChromaDB)
* [x] SQL DB integration (SQLite)
* [x] Arabic language support
* [x] Arabic diacritics normalization support
* [x] Benchmark suite
* [x] RAG integration ready
* [x] **Bonus:** Arabic Text Reshaping (Visual glyph auto-fix)
* [x] **Bonus:** Smart RTL Detection (Presentation Forms logic)
* [x] **Bonus:** Sentence-aware Chunking (with Punctuation & Newline fallback)
* [x] **Bonus:** Real-time document preview in UI with Glassmorphism Design

---

## Architecture

### 🔹 High-Level Design

**1. Ingestion Layer**
* Parses documents using:
  * `PyMuPDF (fitz)` (PDF - with coordinate sorting for RTL)
  * `python-docx` (DOCX)
  * Native TXT loader
* Extracts raw text
* Performs Arabic normalization and visual-to-logical correction.

**2. Content Analysis Module**
* Detects:
  * Structure (Headings like "Chapter", "الفصـل")
  * Visual encoding artifacts (Presentation Forms)
* Selects optimal chunking strategy:
  * **Dynamic Chunking**: Respects semantic boundaries (headings).
  * **Sentence-Aware Chunking**: Uses punctuation and overlapping sliding windows.

**3. Chunking Engine**
* Intelligent implementation that prevents cutting sentences mid-way.
* Overlap support for context preservation.

**4. Embedding Layer**
* `SentenceTransformers` (`paraphrase-multilingual-MiniLM-L12-v2`)
* Optimized for multilingual semantic similarity.

**5. Vector Database**
* **ChromaDB**: Embeddings storage for fast similarity search.

**6. SQL Database**
* **SQLite**: Stores metadata, raw text chunks for auditors, and processing logs.

**7. Retrieval Layer**
* Top-k semantic search via FastAPI endpoint.
* Returns structured results with metadata.

---

## Technologies Used

* Python 3.10+
* FastAPI, Uvicorn
* SentenceTransformers
* ChromaDB
* SQLite
* PyMuPDF (fitz)
* python-docx
* arabic-reshaper, python-bidi (Arabic visual correction)
* Docker & Docker Compose

---

## Benchmark Results

| Metric                       | Result         | Description |
| ---------------------------- | -------------- | ---------------- |
| **Processing Speed**         | `0.68s`        | End-to-end processing for standard doc (`الفص 1.docx`) |
| **Memory Footprint**         | `~110 MB`      | Peak usage during embedding generation |
| **Diacritics Preservation**  | **100.00%**    | Zero loss of semantic meaning |
| **RTL Integrity**            | **100%**       | Visual encoding auto-corrected via Smart Detection |

### Observations:
* **Dynamic/Sentence Chunking** significantly improves retrieval context compared to fixed-size chunking.
* **Smart RTL Detection** resolves the "reversed text" issue common in Arabic PDFs without manual intervention.

---

## How to Run

### 1️⃣ Clone Repository

```bash
git clone https://github.com/abdullahikhmaies/pyxon-ai-entry-task.git
cd pyxon-ai-entry-task
```

### 2️⃣ Install Dependencies (Local)

```bash
pip install -r requirements.txt
```

### 3️⃣ Run Backend

```bash
python -m app.api.server
# Open http://localhost:8000
```

### 4️⃣ Run with Docker (Recommended)

```bash
docker-compose up --build
# API available at http://localhost:8000
```

### 5️⃣ Run Benchmarks

```bash
python app/benchmark/test_suite.py "data/الفص 1.docx"
```

---


---

# ✅ Evaluation Readiness

✔ All functional requirements met
✔ Arabic + diacritics properly handled
✔ Intelligent chunking implemented
✔ Benchmarking included
✔ Modular architecture with Docker support

---

Ready for review and feedback 🚀
