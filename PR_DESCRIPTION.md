# PR Description Template (copy into your Pull Request)

## Summary

AI-powered document parser using LangGraph: ingest graph (extract → analyze → chunk → embed → store) and RAG graph (query → retrieve → optional Graph RAG/RAPTOR → optional LLM). Supports PDF, DOCX, TXT; Chroma + SQLite; full Arabic and diacritics; benchmarks and Streamlit demo.

## Contact Information

- **REQUIRED** – Email: [your-email@example.com] or Phone: [your-phone-number]

## Demo Link

- **REQUIRED** – [Link to live demo, e.g. Hugging Face Spaces or Streamlit Cloud]

## Features Implemented

- [x] Document parsing (PDF, DOCX, TXT)
- [x] Content analysis and chunking strategy selection
- [x] Fixed and dynamic chunking
- [x] Vector DB integration (Chroma)
- [x] SQL DB integration (SQLite)
- [x] Arabic language support
- [x] Arabic diacritics support
- [x] Benchmark suite
- [x] RAG integration ready
- [x] Graph RAG / RAPTOR (optional enhancements)

## Architecture

LangGraph orchestrates two workflows: (1) Ingest: extract text (by format) → analyze content and choose strategy → chunk (fixed or dynamic) → embed → store in Chroma and SQLite. (2) RAG: query → vector retrieve → optional Graph RAG or RAPTOR expansion → optional LLM answer. Graph RAG builds a knowledge graph from chunks; RAPTOR builds a hierarchical tree for multi-level retrieval.

## Technologies Used

LangGraph, LangChain, pypdf, python-docx, sentence-transformers (paraphrase-multilingual-MiniLM), Chroma, SQLite, NetworkX, Streamlit, pytest.

## Benchmark Results

Run `python scripts/run_benchmarks.py` or `pytest benchmarks -v`. Key metrics: retrieval recall@k, chunking coherence, Arabic round-trip, performance (ingest/retrieval latency).

## How to Run

See README section "Implementation (How to Run)": `pip install -r requirements.txt`, set `.env`, then `run_ingest(path)`, `run_rag(query)`, `streamlit run demo/app.py`, `python scripts/run_benchmarks.py`.

## Questions & Assumptions

- Assumption: Text-based PDFs only; OCR is a future improvement.
- Assumption: Graph RAG and RAPTOR use heuristic/lightweight fallbacks (no LLM) for entity extraction and summarization in the demo.

## Future Improvements

- OCR for image-based PDFs.
- LLM-based entity/relation extraction for Graph RAG and summarization for RAPTOR when API key is set.
- Hybrid retrieval (vector + BM25).

---

**After submitting:** Reply to the confirmation email to confirm receipt and your availability.
