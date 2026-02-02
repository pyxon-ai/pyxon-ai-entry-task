import streamlit as st
from main import preprocess_arabic, read_file  # إعادة استخدام دوالك
import chromadb
import numpy as np
from sentence_transformers import SentenceTransformer

# -----------------------------
# إعداد Chroma Client
# -----------------------------
client = chromadb.Client()
try:
    collection = client.get_collection("documents")
except chromadb.errors.NotFoundError:
    collection = client.create_collection("documents")

print("Collection ready:", collection.name)

# -----------------------------
# واجهة Streamlit
# -----------------------------
st.title("Pyxon AI Document Parser Demo")

uploaded_file = st.file_uploader("Upload a PDF, DOCX, or TXT file", type=["pdf", "docx", "txt"])

if uploaded_file is not None:
    # قراءة الملف مؤقتًا
    temp_path = f"temp_{uploaded_file.name}"
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    raw_text = read_file(temp_path)
    clean_text = preprocess_arabic(raw_text)

    # عرض النص العربي بشكل صحيح
    st.subheader("Processed Text Preview")
    st.markdown(f'<div dir="rtl" style="font-size:14px;">{clean_text[:1500]}...</div>', unsafe_allow_html=True)

    # -----------------------------
    # بحث تشابهية (Top 5 chunks)
    # -----------------------------
    model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    query_embedding = model.encode(clean_text).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=5
    )

    st.subheader("Top 5 Similar Chunks in DB")
    for i, (doc_id, text) in enumerate(zip(results['ids'][0], results['documents'][0])):
        st.markdown(f'<b>{i+1}. ID: {doc_id}</b>', unsafe_allow_html=True)
        st.markdown(f'<div dir="rtl" style="font-size:14px;">{text[:500]}...</div>', unsafe_allow_html=True)
