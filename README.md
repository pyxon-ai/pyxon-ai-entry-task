# Document Parser with RAG

AI-powered document parser that supports PDF, DOCX, and TXT files with intelligent chunking and Arabic language support.

## Features

- Document parsing (PDF, DOCX, TXT)
- Intelligent chunking (fixed and dynamic strategies)
- Arabic language support with diacritics
- Vector database (ChromaDB) + SQL database (PostgreSQL)
- Semantic search
- Web interface

## Tech Stack

- FastAPI
- PostgreSQL
- ChromaDB
- Sentence Transformers
- Docker

## Setup

1. Clone the repository
2. Copy `.env.example` to `.env` and configure
3. Run with Docker:
```bash
docker compose up
```

4. Access at http://localhost:8000

## Environment Variables

See `.env.example` for required configuration.

## Project Structure

```
app/
  api/          - API endpoints
  models/       - Database models
  services/     - Business logic
  config.py     - Configuration
frontend/       - Web interface
benchmarks/     - Test suite
tests/          - Unit tests
```

## Usage

1. Upload a document (PDF/DOCX/TXT)
2. Documents are automatically processed and chunked
3. Use search to query document content
4. Supports Arabic text with diacritics

## Running Tests

```bash
python -m pytest tests/
python benchmarks/benchmark_suite.py
```

## Deployment

Built with Docker for easy deployment to any cloud platform.
