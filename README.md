---
title: AI Parser Evaluation Dashboard
emoji: 🔍
colorFrom: blue
colorTo: purple
sdk: gradio
sdk_version: 4.19.0
app_file: app.py
pinned: false
---

# AI Parser Evaluation Dashboard

Hybrid-Cloud RAG System with LLM-as-Judge Evaluation

## Features

- 📤 **Upload Documents** - Process multiple files (PDF, DOCX, TXT)
- 🔍 **Semantic Search** - Vector search with Cohere reranking
- 📊 **SQL Search** - Filter by content, file name, strategy, document ID
- ⚙️ **Run Evaluation** - 15 test questions evaluated by Gemini AI
- 📈 **View Results** - Detailed scores and statistics
- 📋 **Document List** - All uploaded documents

## Tech Stack

- **Frontend:** Gradio
- **Backend:** FastAPI (needs to be running separately)
- **Vector DB:** Weaviate Cloud
- **SQL DB:** Supabase PostgreSQL
- **Embeddings:** Cohere embed-multilingual-v3.0
- **Reranking:** Cohere rerank-multilingual-v3.0
- **LLM Judge:** Gemini 2.0 Flash Exp

## Usage

1. Make sure your FastAPI backend is running
2. Upload test documents
3. Try semantic or SQL search
4. Run evaluation to test the system
5. View results and statistics

## Note

This Space requires a running FastAPI backend. Update `API_BASE_URL` in `app.py` to point to your deployed backend.
