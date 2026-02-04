<<<<<<< HEAD
# Arabic RAG Document Parser

A high-performance, production-ready RAG (Retrieval-Augmented Generation) document parser optimized for Arabic text with diacritics (Harakat) and RTL (Right-to-Left) formatting support.

## 🌟 Features

### 📄 Multi-Format Document Parsing
- **PDF**: Dual-engine support (PyMuPDF & pdfplumber) for robust Arabic extraction
- **DOCX**: Full support for Word documents with tables
- **TXT**: Smart encoding detection (UTF-8, UTF-16, CP1256, ISO-8859-6)

### 🔤 Advanced Arabic Text Processing
- **RTL Correction**: Fixes reversed text from PDF extraction
- **Diacritics Preservation**: Maintains Harakat in original text
- **Dual-Version Creation**: 
  - Retrieval-friendly version (with diacritics)
  - Search-friendly version (normalized for better matching)
- **PDF Error Correction**: Fixes common Arabic PDF extraction issues
- **Named Entity Recognition**: Extracts Arabic organizations, locations, etc.

### ✂️ Intelligent Chunking Strategies
1. **Fixed-Size Chunking**: Standard slicing with configurable overlap
2. **Semantic Chunking**: Structure-aware segmentation based on:
   - Headers and sections
   - Paragraph boundaries
   - Semantic similarity (embedding-based)
3. **Auto-Selector**: Analyzes document structure to choose optimal strategy

### 💾 Dual Storage Architecture
- **Vector Database (ChromaDB)**: Stores embeddings for similarity search
  - Uses `paraphrase-multilingual-MiniLM-L12-v2` model
  - Optimized for Arabic and multilingual content
- **Metadata Database (SQLite)**: Tracks processing history
  - Document metadata (file info, processing timestamps)
  - Chunk metadata (positions, strategy used)
  - Benchmark results

### 📊 Comprehensive Benchmarking Suite
- **Performance Metrics**:
  - Processing time (parsing, chunking, embedding)
  - Memory usage (peak and average)
- **Quality Metrics**:
  - Retrieval accuracy (Hit Rate, MRR)
  - Arabic extraction accuracy (vs ground truth)
  - Word-level precision/recall/F1

## 🏗️ Architecture

```
rag2/
├── core/                      # Core processing modules
│   ├── arabic_processor.py    # Arabic text processing & normalization
│   ├── document_parser.py     # Multi-format document parsing
│   ├── chunking_strategy.py   # Intelligent chunking strategies
│   └── embedding_manager.py   # Embedding generation
├── storage/                   # Storage layer
│   ├── vector_store.py        # ChromaDB integration
│   └── metadata_store.py      # SQLite metadata tracking
├── benchmarks/                # Benchmarking suite
│   └── benchmark_suite.py     # Performance & quality metrics
├── examples/                  # Example scripts
│   ├── example_usage.py       # Basic usage example
│   └── run_benchmark.py       # Benchmark comparison
├── databases/                 # Database storage (auto-created)
├── data/                      # Input documents (auto-created)
├── output/                    # Benchmark results (auto-created)
├── config.py                  # Configuration settings
├── main.py                    # Main RAG pipeline
└── requirements.txt           # Dependencies
```

## 🚀 Quick Start

### Installation

1. **Clone or navigate to the project directory**

2. **Create and activate virtual environment**:
```bash
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

### Basic Usage

```python
from main import ArabicRAGPipeline

# Initialize pipeline
pipeline = ArabicRAGPipeline(
    chunking_strategy='auto',  # or 'fixed', 'semantic'
    device='cpu'               # or 'cuda' for GPU
)

# Process documents
results = pipeline.process_batch([
    'file_ar.pdf',
    'file.txt'
])

# Query the system
query_results = pipeline.query(
    "ما هي خدمات إعادة التدوير؟",
    n_results=5
)

# Display results
for doc in query_results['results']['documents'][0]:
    print(doc)
```

### 🖥️ Streamlit UI (Web Interface)

The project includes a full-featured web interface:

```bash
streamlit run app.py
```

This opens a dashboard where you can:
- Upload and process documents (PDF, DOCX, TXT)
- Choose chunking strategies visually
- Chat with your documents using the **Multi-Agent Orchestrator**
- View retrieval results and processing statistics

### 🤖 Multi-Agent Orchestration

The system features a Multi-Agent architecture combining **RAG** (Retrieval) and **Gemini** (Generation):

```python
from multi_agent import MultiAgentOrchestrator

# Initialize agents
orchestrator = MultiAgentOrchestrator()

# Ask questions related to your docs
result = orchestrator.ask("ما هي خدمات إعادة التدوير؟")
print(result['answer'])
```

**Setup for Multi-Agent:**
1. Ensure `GEMINI_API_KEY` is set in `.env`
2. Run the interactive chat: `python multi_agent.py`

### Run Examples

**Basic example**:
```bash
python examples/example_usage.py
```

**Benchmark comparison**:
```bash
python examples/run_benchmark.py
```

## 🔧 Configuration

Edit `config.py` to customize:

### Chunking Configuration
```python
# Fixed-size chunking
FIXED_CHUNK_SIZE = 512
FIXED_CHUNK_OVERLAP = 128

# Semantic chunking
SEMANTIC_MIN_CHUNK_SIZE = 200
SEMANTIC_MAX_CHUNK_SIZE = 1000
```

### Arabic Processing
```python
# Normalization options
NORMALIZE_ALEF = True
NORMALIZE_HAMZA = True
REMOVE_TATWEEL = True
```

### Embedding Model
```python
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
```

## 📊 Benchmarking

The system includes a comprehensive benchmarking suite:

```python
results = pipeline.run_benchmark(
    file_paths=['file_ar.pdf', 'file.txt'],
    test_queries=[
        "ما هي الخدمات المتوفرة؟",
        "معلومات عن إعادة التدوير",
    ],
    ground_truth_pdf='file_ar.pdf',
    ground_truth_txt='file.txt',
    run_name='my_benchmark'
)
```

**Metrics tracked**:
- Processing time (total and per-chunk)
- Memory usage (peak and average)
- Retrieval accuracy (hit rate, MRR)
- Arabic extraction quality (precision, recall, F1)

Results are saved to:
- `databases/metadata.db` (SQL database)
- `output/[run_name].json` (JSON file)

## 🎯 Key Components

### ArabicTextProcessor
Handles Arabic-specific text processing:
- RTL text correction
- Diacritics preservation
- PDF extraction error fixes
- Dual-version creation (retrieval + search)
- Named entity extraction

### DocumentParser
Multi-format parsing with Arabic support:
- Automatic format detection
- Encoding-aware text extraction
- Table extraction (DOCX)
- Fallback mechanisms

### Chunking Strategies
Three intelligent strategies:
1. **FixedSizeChunker**: Reliable baseline with overlap
2. **SemanticChunker**: Structure-aware or similarity-based
3. **AutoChunker**: Analyzes document to select best strategy

### Storage Layer
- **VectorStore**: ChromaDB for embedding storage
- **MetadataStore**: SQLite for metadata tracking

## 🔬 Arabic Text Processing Logic

The system incorporates advanced logic for Arabic text (adapted from `extract.py`):

### RTL Correction
```python
# Fixes visual RTL order to logical order
# Example: "ةملك" → "كلمة"
processor.fix_rtl_extraction(text)
```

### Common PDF Fixes
```python
# Fixes extraction issues like:
# "اال" → "ال"
# "األ" → "أل"
# "الإعادة" → "لإعادة"
processor.fix_common_pdf_errors(text)
```

### Normalization
```python
# Create search-friendly version
# Removes diacritics, normalizes Alef/Hamza variants
processor.normalize_for_search(text)
```

## 📈 Performance Considerations

### Memory Optimization
- Batch processing with configurable batch size
- Memory monitoring during benchmarking
- Efficient embedding generation

### Processing Speed
- Parallel processing support (configurable workers)
- Optimized chunking algorithms
- Fast vector similarity search

### Quality Assurance
- Dual-version text storage
- Multiple chunking strategies
- Comprehensive benchmarking

## 🧪 Testing with Ground Truth

The system supports testing against ground truth:

```python
# Compare PDF extraction against known-good text file
pipeline.benchmark_suite.benchmark_arabic_extraction(
    parser=pipeline.parser,
    pdf_file='file_ar.pdf',
    ground_truth_file='file.txt'
)
```

Metrics:
- Character-level accuracy
- Word-level precision/recall/F1
- Content preservation

## 🛠️ Advanced Usage

### Custom Chunking Strategy

```python
from core.chunking_strategy import SemanticChunker

# Create custom semantic chunker
chunker = SemanticChunker(
    min_chunk_size=300,
    max_chunk_size=800,
    use_embeddings=True  # Enable similarity-based chunking
)

pipeline = ArabicRAGPipeline(chunking_strategy=chunker)
```

### Filtering Queries

```python
# Query with metadata filter
results = pipeline.query(
    "Arabic query",
    n_results=5,
    filter_metadata={'is_arabic': True}
)
```

### Batch Processing with Custom Metadata

```python
results = pipeline.process_batch(
    file_paths=['doc1.pdf', 'doc2.docx'],
    custom_metadata={'source': 'research_papers', 'year': 2024}
)
```

## 📋 Requirements

- Python 3.8+
- PyMuPDF (fitz)
- pdfplumber
- python-docx
- ChromaDB
- sentence-transformers
- SQLAlchemy
- pandas, numpy
- psutil (for benchmarking)

See `requirements.txt` for complete list.

## 🤝 Contributing

This is a production-ready system designed for Arabic RAG applications. Key areas for contribution:
- Additional document formats
- More advanced NER for Arabic
- Fine-tuned embedding models
- Advanced semantic chunking

## 📝 License

MIT License

## 🙏 Acknowledgments

- Arabic text processing logic adapted and enhanced from specialized extraction utilities
- Multilingual embedding model from sentence-transformers
- Vector database powered by ChromaDB

## 📞 Support

For issues or questions:
1. Check the examples in `examples/`
2. Review configuration in `config.py`
3. Examine logs for detailed error messages

---

**Built with ❤️ for Arabic NLP and RAG applications**
=======
# Pyxon AI - Junior Engineer Entry Task

## Overview

Your task is to build an **AI-powered document parser** that intelligently processes documents, understands their content, and prepares them for retrieval-augmented generation (RAG) systems. The parser should support multiple file formats, intelligent chunking strategies, and full Arabic language support including diacritics (harakat).

## Task Requirements

### 1. Document Parser

Create an AI parser that can:

- **Read multiple file formats:**
  - PDF files
  - DOC/DOCX files
  - TXT files

- **Content Understanding:**
  - Analyze and understand the semantic content of documents
  - Identify document structure, topics, and key concepts
  - Determine the most appropriate chunking strategy based on content

- **Intelligent Chunking:**
  - **Fixed chunking:** For uniform documents (e.g., structured reports, forms)
  - **Dynamic chunking:** For documents with varying structure (e.g., books with chapters, mixed content)
  - The parser should automatically decide which strategy to use based on document analysis

- **Storage:**
  - Save processed chunks to a **Vector Database** (for semantic search)
  - Save metadata and structured information to a **SQL Database** (for relational queries)

- **Arabic Language Support:**
  - Full support for Arabic text
  - Support for Arabic diacritics (harakat/tashkeel)
  - Proper handling of Arabic text encoding and directionality

### 2. Benchmark Suite

Create a comprehensive benchmark to test:

- **Retrieval accuracy:** How well the system retrieves relevant chunks for given queries
- **Chunking quality:** Evaluate if chunks maintain semantic coherence
- **Performance metrics:** Speed, memory usage, and scalability
- **Arabic-specific tests:** Verify proper handling of Arabic text and diacritics

### 3. RAG Integration

The parser should be designed to integrate with a RAG system that:
- Connects to LLMs for question answering
- Uses the vector database for semantic retrieval
- Uses the SQL database for structured queries

## Technical Specifications

### Recommended Approaches

Consider implementing advanced RAG techniques:

1. **Graph RAG:** Use knowledge graphs to represent document relationships and improve retrieval
2. **RAPTOR (Recursive Abstractive Processing for Tree-Organized Retrieval):** Implement hierarchical document understanding and chunking
3. **Hybrid Retrieval:** Combine semantic (vector) and keyword-based retrieval

### Reference Material

- [NotebookLM Processing Sources - RAG Discussion](https://www.reddit.com/r/notebooklm/comments/1h1saih/how_is_notebooklm_processing_sources_rag_brute/)
- Research papers on Graph RAG
- RAPTOR implementation techniques

### Technology Stack

**You are free to use any framework, library, or technology stack of your choice.** The following are suggestions only:

- **Document Processing:** PyPDF2, python-docx, or similar libraries
- **NLP/Embeddings:** Transformers, sentence-transformers, or multilingual models
- **Vector DB:** Chroma, Pinecone, Weaviate, or Qdrant
- **SQL DB:** PostgreSQL, SQLite, or MySQL
- **Arabic NLP:** Consider models like CAMeLBERT, AraBERT, or multilingual models with Arabic support

Choose the tools and frameworks that best fit your implementation approach and expertise.

## Deadline

**Submission Deadline:** Monday, February 2nd, 13:00 Amman time.

**Review Timeline:** Code reviews and candidate calls will be conducted on Tuesday, February 3rd.

## Submission Guidelines

### Process

1. **Fork this repository** to your GitHub account
2. **Implement the solution** following the requirements above
3. **Create a working demo** that can be accessed and tested online
4. **Create a Pull Request** with:
   - **Contact Information** (required) - Your email address or phone number for communication
   - **Demo link** (required) - A live, accessible demo to test the implementation
   - Clear description of what was implemented
   - Architecture decisions and trade-offs
   - How to run the code
   - Benchmark results
   - Any limitations or future improvements
   - **Questions & Assumptions** - If you have any questions about the requirements, list them in the PR along with the assumptions you made to proceed

### Important Notes

- **Reply to emails:** After submitting your PR, you will receive an email. Please reply to confirm receipt and availability.
- **Questions:** If you have any questions or ambiguities about the requirements, include them in your PR description along with the assumptions you made to proceed with the implementation.

### PR Description Template

```markdown
## Summary
Brief overview of the implementation

## Contact Information
📧 Email: [your-email@example.com] or 📱 Phone: [your-phone-number] - **REQUIRED**

## Demo Link
🔗 [Link to live demo] - **REQUIRED**

## Features Implemented
- [ ] Document parsing (PDF, DOCX, TXT)
- [ ] Content analysis and chunking strategy selection
- [ ] Fixed and dynamic chunking
- [ ] Vector DB integration
- [ ] SQL DB integration
- [ ] Arabic language support
- [ ] Arabic diacritics support
- [ ] Benchmark suite
- [ ] RAG integration ready

## Architecture
Description of system design and key components

## Technologies Used
List of libraries and frameworks

## Benchmark Results
Key metrics and performance data

## How to Run
Step-by-step instructions

## Questions & Assumptions
If you had any questions about the requirements, list them here along with the assumptions you made:
- Question 1: [Your question]
  - Assumption: [How you proceeded]
- Question 2: [Your question]
  - Assumption: [How you proceeded]

## Future Improvements
Ideas for enhancement
```

**Note:** The demo link is a **mandatory requirement**. It should allow reviewers to test your implementation with sample documents (including Arabic documents with diacritics) and see the chunking and retrieval in action.

## Evaluation Criteria

Your submission will be evaluated on:

1. **Functionality:** All requirements are met
2. **Code Quality:** Clean, maintainable, well-documented code
3. **Arabic Support:** Proper handling of Arabic text and diacritics
4. **Intelligent Chunking:** Effective strategy selection and implementation
5. **Benchmark Quality:** Comprehensive tests and meaningful metrics
6. **Architecture:** Well-designed, scalable solution
7. **Documentation:** Clear README and code comments

## Questions?

If you have any questions about the requirements, please include them in your PR description along with the assumptions you made to proceed with the implementation. This helps us understand your decision-making process.

Good luck! 🚀
>>>>>>> upstream/main
