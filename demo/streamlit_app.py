import sys
import os
import re

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

import streamlit as st
from app.main import run_pipeline_from_upload
from app.rag.rag_pipeline import RAGPipeline


# -------------------------
# Session State
# -------------------------
if "processed" not in st.session_state:
    st.session_state.processed = False

if "last_file_name" not in st.session_state:
    st.session_state.last_file_name = None

if "doc_info" not in st.session_state:
    st.session_state.doc_info = None


# -------------------------
# Helpers
# -------------------------
def pretty_arabic(text: str) -> str:
    lines = [l.strip() for l in text.split("\n")]
    lines = [l for l in lines if len(l) > 20]
    return " ".join(lines)


def extract_answer(text: str, max_sentences: int = 2) -> str:
    clean = pretty_arabic(text)
    sentences = clean.split("،")
    return "،".join(sentences[:max_sentences]).strip()


def is_arabic(text: str) -> bool:
    return bool(re.search(r"[\u0600-\u06FF]", text))


# -------------------------
# Page config + Header
# -------------------------
st.set_page_config(
    page_title="DocuRAG Parser Demo",
    layout="wide"
)

st.markdown(
    """
    <style>
        .centered-title {
            text-align: center;
            margin-top: 10px;
        }
        .centered-subtitle {
            text-align: center;
            font-size: 18px;
            color: #555;
            margin-bottom: 30px;
        }
        .info-box {
            background-color: #f5f7fa;
            padding: 14px;
            border-radius: 8px;
            border-left: 5px solid #1976d2;
            margin-bottom: 20px;
        }
    </style>

    <h1 class="centered-title">📄 DocuRAG Parser</h1>
    <div class="centered-subtitle">
        AI-powered document parser designed for <b>RAG systems</b><br/>
        Supports <b>PDF, DOCX, TXT</b> with <b>Arabic language & diacritics</b> support.
    </div>
    """,
    unsafe_allow_html=True
)

# -------------------------
# Upload Section
# -------------------------
st.header("1️⃣ Upload Document")

uploaded_file = st.file_uploader(
    "Upload a document (PDF, DOCX, TXT)",
    type=["pdf", "docx", "txt"]
)

if uploaded_file is not None:
    if st.button("🚀 Process Document"):
        if uploaded_file.name == st.session_state.last_file_name:
            st.warning("⚠️ This document has already been processed.")
        else:
            with st.spinner("Processing document..."):
                result = run_pipeline_from_upload(uploaded_file)
                st.session_state.processed = True
                st.session_state.last_file_name = uploaded_file.name
                st.session_state.doc_info = result

            st.success("✅ Document processed successfully!")

# -------------------------
# Document Info Section
# -------------------------
if st.session_state.processed and st.session_state.doc_info:
    info = st.session_state.doc_info

    st.markdown(
        f"""
        <div class="info-box">
            <b>📊 Document Analysis</b><br/>
            <ul>
                <li><b>Language:</b> {info["language"]}</li>
                <li><b>Chunking Strategy:</b> {info["chunking_strategy"]}</li>
                <li><b>Number of Chunks:</b> {info["num_chunks"]}</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True
    )

# -------------------------
# Ask Question Section
# -------------------------
st.divider()
st.header("2️⃣ Ask a Question")

query = st.text_input(
    "Enter your question (Arabic or English)",
    placeholder="مثال: ما هو الذكاء الاصطناعي؟"
)

if query and st.session_state.processed:
    rag = RAGPipeline()

    with st.spinner("Thinking..."):
        result = rag.run(query)

    if not result["retrieved_chunks"]:
        st.warning("No relevant answer found.")
    else:
        best_chunk = result["retrieved_chunks"][0]
        answer = extract_answer(best_chunk["text"])

        rtl = is_arabic(answer)
        direction = "rtl" if rtl else "ltr"
        align = "right" if rtl else "left"
        border_side = "border-right" if rtl else "border-left"
        title = "الإجابة" if rtl else "Answer"

        st.markdown(
            f"""
            <div style="
                direction: {direction};
                text-align: {align};
                background-color: #e8f5e9;
                {border_side}: 6px solid #2e7d32;
                padding: 16px;
                border-radius: 8px;
                font-size: 18px;
                line-height: 1.9;
                color: #1b5e20;
                font-family: 'Segoe UI', Tahoma, Arial;
            ">
                <strong>🧠 {title}:</strong><br><br>
                {answer}
            </div>
            """,
            unsafe_allow_html=True
        )

# -------------------------
# Footer
# -------------------------
st.divider()
st.caption("DocuRAG-Parser | AI Document Processing for RAG Systems")