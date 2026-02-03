# main
import streamlit as st
from pathlib import Path
import tempfile
import uuid
from datetime import datetime

from src.pyxon.parsers import parse_document
from src.pyxon.storage.vs import VectorStore
from src.pyxon.storage.database.repository import SQLStore
from src.pyxon.storage.database.schemas import DocumentCreate, ChunkCreate
from src.pyxon.rag.graph import app as rag_app
from src.pyxon.rag.state import AgentState
from langchain_core.messages import HumanMessage


st.set_page_config(
    page_title="Pyxon AI | Document Intelligence Platform",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    /* Main typography and layout */
    .main-header {
        font-size: 2rem;
        font-weight: 600;
        color: #1f2937;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #6b7280;
        margin-bottom: 2rem;
    }
    
    /* Card components */
    .document-card {
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #e5e7eb;
        margin-bottom: 1rem;
        background-color: #f9fafb;
        transition: all 0.2s ease;
    }
    .document-card:hover {
        border-color: #d1d5db;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    .metric-card {
        padding: 1.5rem;
        border-radius: 0.5rem;
        background-color: #f3f4f6;
        text-align: center;
        border: 1px solid #e5e7eb;
    }
    .metric-card h3 {
        margin: 0;
        font-size: 1.125rem;
        font-weight: 600;
        color: #111827;
    }
    .metric-card p {
        margin: 0.5rem 0 0 0;
        color: #6b7280;
        font-size: 0.875rem;
    }
    
    /* Status badges */
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 0.25rem;
        font-size: 0.875rem;
        font-weight: 500;
        margin-bottom: 0.5rem;
    }
    .status-active {
        background-color: #d1fae5;
        color: #065f46;
    }
    .status-inactive {
        background-color: #fee2e2;
        color: #991b1b;
    }
    
    /* Feature list */
    .feature-list {
        list-style: none;
        padding-left: 0;
    }
    .feature-list li {
        padding: 0.75rem 0;
        border-bottom: 1px solid #e5e7eb;
        color: #374151;
    }
    .feature-list li:last-child {
        border-bottom: none;
    }
    .feature-list li:before {
        content: "▸ ";
        color: #6b7280;
        font-weight: bold;
        margin-right: 0.5rem;
    }
    
    /* Button styling */
    .stButton>button {
        width: 100%;
        border-radius: 0.375rem;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    
    /* Document list styling */
    .doc-filename {
        font-weight: 600;
        color: #111827;
        font-size: 0.9rem;
        margin-bottom: 0.25rem;
    }
    .doc-metadata {
        color: #6b7280;
        font-size: 0.8rem;
    }
    
    /* Divider styling */
    hr {
        margin: 1.5rem 0;
        border-color: #e5e7eb;
    }
    
    /* Section headers */
    .section-header {
        font-size: 0.875rem;
        font-weight: 600;
        color: #374151;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

if "document_id" not in st.session_state:
    st.session_state.document_id = None
if "filename" not in st.session_state:
    st.session_state.filename = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "all_documents" not in st.session_state:
    st.session_state.all_documents = []


def get_all_documents():
    """Retrieve all documents from the database."""
    from src.pyxon.storage.database.database import SessionLocal
    from src.pyxon.storage.database.models import Document
    
    session = SessionLocal()
    try:
        docs = session.query(Document).order_by(Document.created_at.desc()).all()
        return [{
            "id": doc.id,
            "filename": doc.filename,
            "doc_type": doc.doc_type,
            "total_chunks": doc.total_chunks,
            "created_at": doc.created_at
        } for doc in docs]
    finally:
        session.close()


def process_uploaded_file(uploaded_file) -> str:
    """Save uploaded file, parse it, chunk it, store in both databases."""
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp:
        tmp.write(uploaded_file.getbuffer())
        tmp_path = tmp.name
    
    with st.spinner("Parsing document..."):
        doc = parse_document(tmp_path, advanced=True)
    
    vs = VectorStore()
    sql_store = SQLStore()
    
    doc_id = str(uuid.uuid4())
    
    with st.spinner("Saving to database..."):
        doc_schema = DocumentCreate(
            filename=uploaded_file.name,
            source_path=tmp_path,
            doc_type=Path(uploaded_file.name).suffix.lstrip(".")
        )
        sql_doc_id = sql_store.save_document(doc_schema)
    
    with st.spinner("Chunking and processing..."):
        chunks = vs.chunk_document(doc)
    
    with st.spinner("Creating embeddings..."):
        vs.add_documents(chunks, sql_doc_id)
    
    with st.spinner("Finalizing storage..."):
        chunk_schemas = [
            ChunkCreate(
                chunk_index=i,
                chunk_text=chunk.page_content
            )
            for i, chunk in enumerate(chunks)
        ]
        sql_store.save_chunks(sql_doc_id, chunk_schemas)
    
    Path(tmp_path).unlink()
    
    return sql_doc_id


def run_rag_query(question: str, document_id: str) -> str:
    """Execute the RAG pipeline on the provided question."""
    
    initial_state: AgentState = {
        "messages": [HumanMessage(content=question)],
        "queries": [question],
        "critiques": [],
        "iteration": 0,
        "should_continue": True,
        "retrieved_docs": [],
        "reranked_docs": [],
        "top_k": 5,
        "metadata_filter": {"document_id": document_id},
        "answer": ""
    }
    
    with st.spinner("Processing query..."):
        final_state = rag_app.invoke(initial_state)
    
    return final_state["answer"]


st.markdown('<div class="main-header">Pyxon AI | Document Intelligence Platform</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Advanced retrieval-augmented generation for document analysis</div>', unsafe_allow_html=True)

with st.sidebar:
    st.markdown('<div class="section-header">Document Management</div>', unsafe_allow_html=True)
    
    tab = st.radio("", ["Upload New", "Existing Documents"], label_visibility="collapsed")
    
    st.divider()
    
    if tab == "Upload New":
        st.markdown("**Upload Document**")
        uploaded_file = st.file_uploader(
            "Select file",
            type=["txt", "pdf", "doc", "docx"],
            help="Supported formats: TXT, PDF, DOC, DOCX",
            label_visibility="collapsed"
        )
        
        if uploaded_file:
            st.info(f"Selected: {uploaded_file.name}")
            
            if st.button("Process Document", type="primary", use_container_width=True):
                try:
                    doc_id = process_uploaded_file(uploaded_file)
                    st.session_state.document_id = doc_id
                    st.session_state.filename = uploaded_file.name
                    st.session_state.chat_history = []
                    st.session_state.all_documents = get_all_documents()
                    st.success("Document processed successfully")
                    st.rerun()
                except Exception as e:
                    st.error(f"Processing error: {str(e)}")
    
    else:
        st.session_state.all_documents = get_all_documents()
        
        if st.session_state.all_documents:
            st.markdown(f'<div class="section-header">Available Documents ({len(st.session_state.all_documents)})</div>', unsafe_allow_html=True)
            
            for doc in st.session_state.all_documents:
                with st.container():
                    st.markdown(f'<div class="doc-filename">{doc["filename"]}</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="doc-metadata">{doc["total_chunks"]} chunks • {doc["created_at"].strftime("%Y-%m-%d %H:%M")}</div>', unsafe_allow_html=True)
                    
                    if st.button("Load Document", key=f"load_{doc['id']}", use_container_width=True):
                        st.session_state.document_id = doc['id']
                        st.session_state.filename = doc['filename']
                        st.session_state.chat_history = []
                        st.rerun()
                    st.divider()
        else:
            st.info("No documents available")
    
    st.divider()
    

    st.markdown('<div class="section-header">Current Session</div>', unsafe_allow_html=True)
    if st.session_state.document_id:
        st.markdown('<div class="status-badge status-active">● Active</div>', unsafe_allow_html=True)
        st.markdown(f"**{st.session_state.filename}**")
        if st.button("Clear Session", use_container_width=True):
            st.session_state.document_id = None
            st.session_state.filename = None
            st.session_state.chat_history = []
            st.rerun()
    else:
        st.markdown('<div class="status-badge status-inactive">○ No Active Document</div>', unsafe_allow_html=True)
    
    st.divider()
    
    st.markdown('<div class="section-header">Resources</div>', unsafe_allow_html=True)
    st.markdown("[View Evaluation Report](https://github.com/ahmad-alqaisi215/pyxon-ai-entry-task/blob/main/tests/rageval.ipynb)")

if st.session_state.document_id:
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    
    if prompt := st.chat_input("Enter your question about the document..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        try:
            answer = run_rag_query(prompt, st.session_state.document_id)
            
            st.session_state.chat_history.append({"role": "assistant", "content": answer})
            with st.chat_message("assistant"):
                st.markdown(answer)
                
        except Exception as e:
            error_msg = f"Error processing query: {str(e)}"
            st.session_state.chat_history.append({"role": "assistant", "content": error_msg})
            with st.chat_message("assistant"):
                st.error(error_msg)

else:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### Getting Started")
        st.markdown("""
        This platform enables intelligent document analysis through advanced retrieval-augmented generation technology. 
        
        **Workflow:**
        1. Upload or select a document from the sidebar
        2. Wait for document processing and indexing
        3. Query the document using natural language
        4. Receive contextually relevant answers
        
        The system supports multiple document formats and provides accurate, source-based responses powered by state-of-the-art RAG architecture.
        """)
    
    with col2:
        st.markdown("### System Capabilities")
        st.markdown("""
        <ul class="feature-list">
            <li>Intelligent document chunking</li>
            <li>Semantic search with reranking</li>
            <li>Self-reflective retrieval</li>
            <li>Dual storage architecture</li>
            <li>Multi-language support</li>
        </ul>
        """, unsafe_allow_html=True)
    
    st.divider()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown('<div class="metric-card"><h3>Vector Search</h3><p>High-precision semantic retrieval using advanced embeddings</p></div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card"><h3>SQL Storage</h3><p>Structured metadata and document management</p></div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-card"><h3>RAG Pipeline</h3><p>Context-aware response generation with source attribution</p></div>', unsafe_allow_html=True)