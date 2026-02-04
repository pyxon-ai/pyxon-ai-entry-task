## Summary
Implemented an advanced AI-powered document parser specializing in Arabic content. The system parses PDF, DOCX, and TXT files, applies specialized Arabic processing (RTL correction, diacritic handling), and uses intelligent chunking strategies (Fixed, Semantic, Auto) to prepare data for RAG. It integrates with ChromaDB for vector storage and SQLite for metadata, featuring a complete Streamlit web interface for interaction and benchmarking.

## Contact Information
📧 Email: abu2002assi@gmail.com
📱 Phone: 0781277516
👤 Name: Abdelrahman Abuassi

## Demo Link
🔗 [https://abodassi-pyxon-ai-entry-task-app-veb4to.streamlit.app/](https://abodassi-pyxon-ai-entry-task-app-veb4to.streamlit.app/)

## Features Implemented
- [x] Document parsing (PDF, DOCX, TXT)
- [x] Content analysis and chunking strategy selection (Auto-mode)
- [x] Fixed and dynamic (Semantic) chunking
- [x] Vector DB integration (ChromaDB)
- [x] SQL DB integration (SQLite)
- [x] Arabic language support (RTL text fixing, normalization)
- [x] Arabic diacritics support (Preservation in retrieval text)
- [x] Benchmark suite (Performance & Accuracy metrics)
- [x] RAG integration ready (Embeddings + Vector Search)

## Architecture
The system is built as a modular pipeline:
1.  **Core Processing**:
    *   `DocumentParser`: Handles file ingestion with specialized engines (`pdfplumber` for robust PDF extraction, `python-docx`).
    *   `ArabicTextProcessor`: Corrects common PDF extraction errors (reversed text, broken ligatures), handles diacritics, and normalizes text for optimized search.
    *   `ChunkingStrategy`:
        *   **Fixed**: Sliding window approach for uniform content.
        *   **Semantic**: Structure-aware splitting (headers/paragraphs) to preserve context.
        *   **Auto**: Analyzes content density and structure to automatically pick the best strategy.
    *   `EmbeddingManager`: Generates embeddings using `paraphrase-multilingual-MiniLM-L12-v2`.
2.  **Storage**:
    *   **VectorStore (ChromaDB)**: Stores document embeddings for semantic retrieval.
    *   **MetadataStore (SQLite)**: Logs processing runs, file metadata, and benchmark results.
3.  **UI/Interaction**:
    *   **Streamlit App**: Provides a web interface for file upload, configuration, visual benchmarking, and Multi-Agent chat (powered by Google Gemini).

## Technologies Used
*   **Language**: Python 3.11
*   **NLP & AI**: LangChain, Sentence-Transformers, Google Gemini (via API)
*   **Databases**: ChromaDB (Vector), SQLite (Relational)
*   **File Processing**: PyMuPDF (fitz), pdfplumber, python-docx
*   **Interface**: Streamlit

## Benchmark Results
Tests were conducted on [file_ar.pdf](cci:7://file:///c:/Users/famil/rags/rag2/file_ar.pdf:0:0-0:0) (1.4MB) and [file.txt](cci:7://file:///c:/Users/famil/rags/rag2/file.txt:0:0-0:0) (33KB) using an Intel Core CPU.

**Pipeline Metrics (Full Run)**:
*   **Total Processing Time**: 37.67s (Parsing: 22.90s, Embedding: 14.76s)
*   **Peak Memory Usage**: 1.29 GB
*   **Arabic Text Extraction Quality (Word F1)**: 32.65% (Comparing PDF extraction vs provided text file)

**Strategy Comparison (Single PDF):**
| Strategy | Chunks Generated | Processing Time | Notes |
|----------|------------------|-----------------|-------|
| **Fixed**| 258              | 37.13s          | Balanced speed/granularity |
| **Semantic**| 97            | 36.47s          | Fewer, context-rich chunks |
| **Auto** | 258              | 45.73s          | Selected 'Fixed' for this file |

## How to Run
1.  **Clone the repository**:
    ```bash
    git clone [https://github.com/abodassi/pyxon-ai-entry-task.git](https://github.com/abodassi/pyxon-ai-entry-task.git)
    cd pyxon-ai-entry-task
    ```
2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Run the Web Application**:
    ```bash
    streamlit run app.py
    ```
4.  **Run Benchmark Suite**:
    ```bash
    # Ensure file_ar.pdf and file.txt are in the root directory
    python examples/run_benchmark.py
    ```

