import streamlit as st
import os
from langchain_community.document_loaders import PyMuPDFLoader, UnstructuredWordDocumentLoader, TextLoader
from langchain_experimental.text_splitter import SemanticChunker
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

st.set_page_config(page_title="Pyxon AI Parser", layout="wide")
st.title("📄 AI Document Parser (Arabic Supported)")


@st.cache_resource
def load_models():
    embed_model = HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    return embed_model


embed_model = load_models()


def process_file(uploaded_file):
    file_path = f"temp_{uploaded_file.name}"
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    ext = os.path.splitext(file_path)[-1].lower()
    if ext == '.pdf':
        loader = PyMuPDFLoader(file_path)
    elif ext in ['.doc', '.docx']:
        loader = UnstructuredWordDocumentLoader(file_path)
    else:
        loader = TextLoader(file_path, encoding='utf-8')

    docs = loader.load()
    os.remove(file_path)
    return docs


uploaded_file = st.file_uploader("ارفع ملف (PDF, DOCX, TXT)", type=['pdf', 'docx', 'txt'])

if uploaded_file:
    with st.spinner("جاري تحليل النص بالذكاء الاصطناعي..."):
        raw_docs = process_file(uploaded_file)

        text_splitter = SemanticChunker(embed_model)
        chunks = text_splitter.split_documents(raw_docs)

        vector_db = Chroma.from_documents(chunks, embed_model)

        st.success(f"تمت معالجة المستند بنجاح! تم تقسيمه إلى {len(chunks)} مقطع ذكي.")

    query = st.text_input("اسأل سؤالاً عن محتوى الملف (مثلاً: ما هي النقاط الأساسية؟):")
    if query:
        results = vector_db.similarity_search(query, k=3)

        st.subheader("النتائج المستخرجة:")
        for i, res in enumerate(results):
            with st.expander(f"مقطع صلة #{i + 1}"):
                st.write(res.page_content)