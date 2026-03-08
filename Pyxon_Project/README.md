## Summary

Pyxon AI is a powerful, local-first Retrieval-Augmented Generation (RAG) backend designed for accurate semantic document search. It features a custom NLP chunking pipeline that preserves semantic boundaries and a Flask web interface designed to natively support Right-to-Left (RTL) Arabic text.
## Contact Information
📧 Email: [yalfares@outlook.com] or 📱 Phone:+966 532196924 - **REQUIRED**

## Demo Link
🔗 https://huggingface.co/spaces/yasminalfares/Pyxon

## Features Implemented
- [*] Document parsing (PDF, DOCX, TXT)
- [*] Content analysis and chunking strategy selection
- [*] Fixed and dynamic chunking
- [*] Vector DB integration
- [*] SQL DB integration
- [*] Arabic language support
- [*] Arabic diacritics support
- [*] Benchmark suite
- [*] RAG integration ready

## Architecture
1.  **Parser (`src/parser.py`):** Ingests raw files (PDF, DOCX, TXT) and normalizes the text (handling artifacts like mid-sentence PDF carriage returns).
2.  **Analyzer (`src/analyzer.py`):** Structurally analyzes the text to determine the optimal chunking strategy (e.g., detecting if a document is mostly short paragraphs vs long continuous text).
3.  **Chunker (`src/chunker.py`):** The core NLP engine. Uses NLTK's `punkt` tokenizer to split text strictly at semantic sentence boundaries, guaranteeing that no chunks contain fragmented words or half-sentences.
4.  **Storage Engine (`src/storage.py`):** A dual-database system. 
    *   **SQLite** handles relational metadata (filenames, upload timestamps).
    *   **ChromaDB** handles the heavy mathematical embedding vectors for semantic similarity search.

## Technologies Used
**Backend Framework:** Python 3.10, Flask, Werkzeug
*   **NLP & Chunking:** NLTK (Natural Language Toolkit)
*   **Vector Embeddings:** `sentence-transformers` (Model: `paraphrase-multilingual-mpnet-base-v2`)
*   **Vector Database:** ChromaDB
*   **Relational Database:** SQLite
*   **Document Parsing:** `PyMuPDF` (PDFs), `python-docx` (Word Documents)
*   **Frontend UI:** Vanilla HTML5, CSS3 (Glassmorphism), JavaScript (Fetch API)
*   **Deployment:** Docker



## How to Run

If you are cloning this repository to your own machine, follow these steps to start the web server.

### Prerequisites
You must have Python 3.10+ installed on your computer.

### Installation
1.  **Clone the Repository**
    ```bash
    git clone https://github.com/your-username/Pyxon.git
    cd Pyxon
    ```
2.  **Create a Virtual Environment (Recommended)**
    ```bash
    python -m venv venv
    venv\\Scripts\\activate  # On Windows
    # source venv/bin/activate  # On Mac/Linux
    ```
3.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

### Running the App
1.  Start the Flask server:
    ```bash
    python app.py
    ```
2.  Open your internet browser and navigate to:
    ```
    http://127.0.0.1:7860
    ```
3.  Drag and drop your PDFs into the "Knowledge Base" zone. Note: The first time you upload a document, it will take some time to load.


## Future Improvements
Pipe extracted chunks into an LLM to generate natural-sounding answers.  
