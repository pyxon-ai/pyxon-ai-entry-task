# AI Parser - Submission Documentation

## Contact Information
- **Name:** Eyad Al-Naimi
- **Email:** efalnaimi22@gmail.com
- **Phone:** 962782608645

---

## Demo Link
🔗 **Live Demo:** https://pyxon-ai-entry-task-f8eh7ukegkhjtyyabxb9v5.streamlit.app/

---

## Implementation Description

### Overview
AI Parser is an intelligent document chunking and semantic search system that processes documents (PDF, DOCX, TXT) and enables powerful semantic retrieval using vector embeddings.

### Key Features
1. **Dynamic Chunking Strategy**
   - AI-powered decision (Gemini 2.5 Flash) to choose between fixed-size or semantic chunking
   - Optimizes chunk quality based on document complexity

2. **Hybrid Storage Architecture**
   - **Weaviate Cloud**: Vector embeddings for semantic search
   - **Supabase PostgreSQL**: Document metadata and SQL queries

3. **Semantic Search with Reranking**
   - Cohere `embed-multilingual-v3.0` for 1024-dim embeddings
   - Cohere `rerank-multilingual-v3.0` for result quality improvement
   - Supports Arabic and multilingual content

4. **Multi-File Upload**
   - Batch processing with independent error handling
   - Automatic rollback on failures

---

## Architecture Decisions & Trade-offs

### 1. Hybrid Cloud Storage (Weaviate + Supabase)
**Decision:** Use cloud-hosted databases instead of local infrastructure.

| Pros | Cons |
|------|------|
| No local hardware requirements | Data hosted externally |
| Free tiers available | Dependency on third-party services |
| Scalable without infrastructure | Network latency |

**Rationale:** 
- We aimed to keep the application as lightweight as possible
- Limited local hardware resources - running databases locally wasn't feasible
- Cloud services (Weaviate Cloud + Supabase) offer free tiers suitable for this project
- Trade-off: We acknowledge that self-hosted solutions would provide better data governance, but cloud hosting was the practical choice given our constraints

---

### 2. Cohere vs OpenAI Embeddings
**Decision:** Chose Cohere's multilingual model.

| Factor | Cohere | OpenAI |
|--------|--------|--------|
| **Free Tier** | ✅ Generous free tier | ❌ No free tier |
| **Arabic Support** | ✅ Strong multilingual | ✅ Good |
| **Reranking** | ✅ Built-in rerank API | ❌ Not available |

**Rationale:** 
- Primary reason: Cohere offers a **free tier** suitable for development and demos
- Added benefit: Native reranking API improves search quality without extra cost

---

### 3. AI-Driven Chunking Strategy
**Decision:** Use Gemini AI to decide chunking strategy per document.

| Approach | Benefit |
|----------|---------|
| Fixed-size | Fast, predictable |
| Semantic | Better context preservation |
| **Dynamic (AI)** | Best of both worlds |

**Trade-off:** Added API call overhead for improved chunk quality.

---

### 4. Stateless API Design
**Decision:** No file storage, direct streaming processing.

| Pros | Cons |
|------|------|
| No storage costs | No file re-processing |
| Privacy-friendly | Requires re-upload |
| Simpler architecture | No file history |

---

## Benchmark Results

### Retrieval Accuracy Test
Tested with **15 diverse Arabic questions** across different document types and topics.

| Metric | Result |
|--------|--------|
| **Total Questions** | 15 |
| **Successful Retrievals** | 15 |
| **Success Rate** | **100%** |

### Test Coverage
- 📄 **PDF**: كأس العالم.pdf (3 questions)
- 📝 **TXT**: الرياضيات, قصة قصيرة, معاذ بن جبل, الاعراق, عشوائي (10 questions)
- 📑 **DOCX**: المعادن.docx (2 questions)

### Key Observations
1. Semantic search correctly identified source documents
2. Reranking significantly improved result relevance
3. Arabic content handled effectively with multilingual embeddings

---

## Questions & Assumptions

### Assumptions Made
1. **File Size Limit:** Assumed 10MB max per file is sufficient
2. **Chunk Size:** Default 500 tokens with 25 overlap for optimal retrieval
3. **Supabase Schema:** Assumed provided schema (documents, chunks tables)
4. **API Rate Limits:** Assumed reasonable usage within free tier limits
5. **Document Complexity:** Assumed documents have maybe a straightforward text structure not that complex layouts for example tables, or OCR requirements. Used familiar text extractors (PyMuPDF, python-docx) due to time constraints - better alternatives may exist for complex documents

### Design Questions Considered
1. **Why not use Weaviate's built-in vectorizer?**
   - Chose Cohere for better multilingual support and reranking

2. **Why Streamlit instead of React frontend?**
   - Faster development, easier deployment, sufficient for demo

3. **Why not store files permanently?**
   - Privacy concerns, simplified architecture, cost efficiency

---

## Technology Stack

| Component | Technology |
|-----------|------------|
| Backend | FastAPI |
| Frontend | Streamlit |
| Vector DB | Weaviate Cloud |
| SQL DB | Supabase PostgreSQL |
| Embeddings | Cohere embed-multilingual-v3.0 |
| Reranking | Cohere rerank-multilingual-v3.0 |
| AI Strategy | Google Gemini 2.5 Flash |
| Document Processing | LangChain, PyMuPDF |

---

## Repository Structure
```
ai-parser/
├── streamlit_app.py          # Main Streamlit UI
├── requirements.txt          # Dependencies
├── .streamlit/config.toml    # Theme configuration
└── src/
    ├── main.py               # FastAPI entry point
    ├── helpers/config.py     # Settings management
    ├── services/
    │   ├── weaviate_client.py
    │   ├── supabase_client.py
    │   └── storage_service.py
    ├── controllers/
    │   ├── DynamicController.py
    │   ├── FixedController.py
    │   └── SemanticController.py
    └── routes/
        ├── chunk.py
        └── search.py
```

---

**Thank you for reviewing this submission!** 🚀
