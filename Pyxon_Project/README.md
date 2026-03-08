# Pyxon AI: Intelligent Document Parsing & Retrieval

Pyxon is a powerful, local-first Retrieval-Augmented Generation (RAG) backend designed for accurate semantic document search. It features a custom NLP chunking pipeline that preserves semantic boundaries and a lightweight, beautiful Flask web interface designed to natively support Right-to-Left (RTL) Arabic text.

## Features
*   **Semantic NLTK Chunking:** Intelligently splits PDFs, DOCX, and TXT files using natural sentence boundaries, entirely avoiding mid-word or mid-sentence cuts.
*   **Advanced Semantic Search:** Utilizes the `paraphrase-multilingual-mpnet-base-v2` embedding model from Hugging Face for deep conceptual understanding of both English and Arabic texts.
*   **Persistent Storage:** Metadata is stored in a clean SQLite database, while vector embeddings are instantly stored and retrieved via ChromaDB.
*   **Dynamic UI Dropdown:** Search across your entire Knowledge Base or restrict your query to a specific, recently uploaded file using the dynamic UI dropdown.
*   **Native Arabic Support:** Flawlessly handles bidirectional text and Arabic queries via the web interface.

---

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



