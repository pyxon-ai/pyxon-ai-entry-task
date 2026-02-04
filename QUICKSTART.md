# Quick Start Guide

This guide will help you get the Pyxon AI Document Parser up and running quickly.

## Prerequisites

- Python 3.12 or higher
- PostgreSQL 13+ with pgvector extension
- OpenAI API key (optional, for LLM features)
- Anthropic API key (optional, alternative to OpenAI)

## Installation

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd pyxon-ai-entry-task
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up PostgreSQL

```bash
# Install PostgreSQL and pgvector extension
# On Ubuntu/Debian:
sudo apt-get install postgresql postgresql-contrib
sudo apt-get install postgresql-13-pgvector

# On macOS (with Homebrew):
brew install postgresql
brew install pgvector

# Start PostgreSQL
sudo service postgresql start  # Linux
brew services start postgresql  # macOS
```

### 5. Create Database

```bash
# Create database
createdb pyxon_docs

# Enable pgvector extension
psql -d pyxon_docs -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### 6. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and set your configuration:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/pyxon_docs
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

### 7. Initialize Database

```bash
python scripts/init_db.py
```

## Running the Demo

### Start the Web Server

```bash
python scripts/run_demo.py
```

The demo will be available at: `http://localhost:8000`

### Using the Demo Interface

1. **Upload Documents**: Click "Choose File" to upload PDF, DOCX, or TXT files
2. **Ask Questions**: Enter questions in English or Arabic
3. **View Documents**: See all processed documents with metadata
4. **Run Benchmarks**: Test retrieval accuracy, Arabic support, and performance

## Running Benchmarks

```bash
python scripts/run_benchmarks.py
```

This will run comprehensive tests and generate a `benchmark_report.md` file.

## Testing with Sample Documents

The project includes sample documents for testing:

- `sample_documents/arabic_with_diacritics.txt` - Arabic text with harakat
- `sample_documents/english_sample.txt` - English text

Upload these through the demo interface to test the system.

## API Endpoints

### Upload Document
```bash
curl -X POST http://localhost:8000/api/documents/upload \
  -F "file=@document.pdf"
```

### Query Documents
```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is this document about?", "top_k": 5}'
```

### List Documents
```bash
curl http://localhost:8000/api/documents
```

### Run Benchmarks
```bash
curl http://localhost:8000/api/benchmarks
```

### Get Statistics
```bash
curl http://localhost:8000/api/stats
```

## Architecture Overview

### Core Components

- **Document Parser** (`src/parsers/`): Parses PDF, DOCX, and TXT files using Docling
- **Chunking Strategies** (`src/chunking/`): Intelligent chunking (fixed, dynamic, auto)
- **Embedding Generator** (`src/embeddings/`): BGE-M3 embeddings for multilingual support
- **Arabic Processor** (`src/arabic/`): CAMeL Tools for Arabic NLP and diacritics
- **RAG System** (`src/rag/`): Retrieval and generation pipeline
- **Database** (`src/database/`): PostgreSQL + pgvector for storage
- **Web API** (`src/api/`): FastAPI interface
- **Benchmark Suite** (`src/benchmarks/`): Comprehensive testing

### Data Flow

1. Upload document → Parse with Docling
2. Detect language and structure → Select chunking strategy
3. Generate chunks → Create embeddings with BGE-M3
4. Store in PostgreSQL + pgvector
5. Query → Retrieve relevant chunks → Generate answer with LLM

## Troubleshooting

### PostgreSQL Connection Issues

```bash
# Check if PostgreSQL is running
sudo service postgresql status

# Check if pgvector is installed
psql -d pyxon_docs -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
```

### Model Download Issues

BGE-M3 and CAMeL Tools will download models on first use. Ensure you have:
- Stable internet connection
- Sufficient disk space (~2GB)

### Arabic Text Issues

If Arabic text appears incorrectly:
- Ensure UTF-8 encoding is used
- Check font support in your browser
- Verify diacritics are preserved

## Development

### Running Tests

```bash
pytest tests/
```

### Code Structure

```
pyxon-ai-entry-task/
├── src/
│   ├── api/           # FastAPI web interface
│   ├── arabic/        # Arabic NLP processing
│   ├── benchmarks/    # Testing suite
│   ├── chunking/      # Chunking strategies
│   ├── config/        # Configuration management
│   ├── database/      # Database models and connections
│   ├── embeddings/    # BGE-M3 embedding generation
│   ├── models/        # Data models
│   ├── parsers/       # Document parsing
│   ├── processor/     # Main document processor
│   ├── rag/           # RAG system
│   └── utils/         # Utility functions
├── demo/              # Web interface
├── scripts/           # Utility scripts
├── tests/             # Test suite
└── sample_documents/  # Sample files
```

## Next Steps

1. Upload your own documents through the web interface
2. Experiment with different chunking strategies
3. Test Arabic queries with diacritics
4. Run benchmarks to evaluate performance
5. Customize the system for your use case

## Support

For issues or questions, please refer to the main README.md or create an issue in the repository.
