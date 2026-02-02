import streamlit as st
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from helpers.config import get_settings
from services.weaviate_client import weaviate_client
from services.supabase_client import supabase_client
from controllers.DynamicController import DynamicController
from controllers.DataController import DataController
from services.storage_service import storage_service
import cohere
import tempfile

st.set_page_config(
    page_title="AI Parser",
    page_icon="🔍",
    layout="wide"
)

settings = get_settings()

st.title("🔍 AI Parser")
st.markdown("**Intelligent Document Chunking & Semantic Search**")

tab1, tab2, tab3 = st.tabs(["📤 Upload", "🔎 Semantic Search", "📊 SQL Search"])

with tab1:
    st.header("Upload Documents")
    
    uploaded_files = st.file_uploader(
        "Choose files",
        type=["pdf", "txt", "docx"],
        accept_multiple_files=True
    )
    
    if uploaded_files and st.button("🚀 Process Files", type="primary"):
        progress = st.progress(0)
        results = []
        
        for idx, file in enumerate(uploaded_files):
            with st.spinner(f"Processing {file.name}..."):
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.name)[1]) as tmp:
                        tmp.write(file.read())
                        tmp_path = tmp.name
                    
                    from fastapi import UploadFile
                    from io import BytesIO
                    
                    file.seek(0)
                    
                    class MockUploadFile:
                        def __init__(self, file_obj):
                            self.filename = file_obj.name
                            self.content_type = file_obj.type
                            self._file = file_obj
                        
                        async def read(self):
                            return self._file.read()
                    
                    mock_file = MockUploadFile(file)
                    
                    dynamic_controller = DynamicController()
                    
                    import asyncio
                    loop = asyncio.new_event_loop()
                    result = loop.run_until_complete(
                        dynamic_controller.process_document(
                            file=mock_file,
                            chunk_size=500,
                            overlap_size=25
                        )
                    )
                    
                    chunks = result["chunks"]
                    strategy = result["strategy"]
                    
                    storage_result = loop.run_until_complete(
                        storage_service.store_document(
                            file_name=file.name,
                            strategy=strategy,
                            chunks=chunks
                        )
                    )
                    loop.close()
                    
                    results.append({
                        "file": file.name,
                        "strategy": strategy,
                        "chunks": len(chunks),
                        "document_id": storage_result["document_id"],
                        "status": "✅ Success"
                    })
                    
                    os.unlink(tmp_path)
                    
                except Exception as e:
                    results.append({
                        "file": file.name,
                        "status": f"❌ Error: {str(e)}"
                    })
                
                progress.progress((idx + 1) / len(uploaded_files))
        
        st.success(f"Processed {len(uploaded_files)} file(s)")
        st.dataframe(results)

with tab2:
    st.header("Semantic Search")
    
    query = st.text_input("🔍 Enter your search query", placeholder="e.g., What is machine learning?")
    limit = st.slider("Number of results", 1, 20, 5)
    
    if st.button("Search", key="semantic_search"):
        if query:
            with st.spinner("Searching..."):
                try:
                    cohere_client = cohere.Client(settings.COHERE_API_KEY)
                    
                    embedding_response = cohere_client.embed(
                        texts=[query],
                        model='embed-multilingual-v3.0',
                        input_type='search_query',
                        embedding_types=['float']
                    )
                    query_vector = embedding_response.embeddings.float[0]
                    
                    initial_results = weaviate_client.semantic_search(
                        query_vector=query_vector,
                        limit=limit * 2
                    )
                    
                    if initial_results:
                        documents = [r["content"] for r in initial_results]
                        rerank_response = cohere_client.rerank(
                            query=query,
                            documents=documents,
                            model='rerank-multilingual-v3.0',
                            top_n=limit
                        )
                        
                        st.success(f"Found {len(rerank_response.results)} results")
                        
                        for i, result in enumerate(rerank_response.results):
                            original = initial_results[result.index]
                            with st.expander(f"📄 Result {i+1} | Score: {result.relevance_score:.3f} | {original.get('file_name', 'Unknown')}"):
                                st.markdown(f"**Content:**\n{original['content']}")
                                st.markdown(f"**Document ID:** {original.get('document_id')}")
                    else:
                        st.info("No results found")
                        
                except Exception as e:
                    st.error(f"Error: {str(e)}")
        else:
            st.warning("Please enter a search query")

with tab3:
    st.header("SQL Search")
    
    search_type = st.radio("Search by:", ["Document Name", "Document ID"], horizontal=True)
    
    if search_type == "Document Name":
        file_name_filter = st.text_input("File name", placeholder="e.g., report.pdf")
        sql_limit = st.slider("Number of results", 1, 50, 20, key="sql_limit")
        
        if st.button("Search", key="sql_search"):
            if file_name_filter:
                with st.spinner("Searching..."):
                    try:
                        results = supabase_client.search_by_document_name(file_name_filter, sql_limit)
                        
                        if results:
                            st.success(f"Found {len(results)} document(s)")
                            
                            for doc in results:
                                with st.expander(f"📄 {doc.get('file_name', 'Unknown')} (ID: {doc['id']})"):
                                    st.markdown(f"**Strategy:** {doc.get('strategy_used', 'N/A')}")
                                    st.markdown(f"**Created:** {doc.get('created_at', 'N/A')}")
                                    
                                    if st.button(f"View Chunks", key=f"chunks_{doc['id']}"):
                                        chunks = supabase_client.get_chunks_by_document(doc['id'])
                                        st.write(f"Total chunks: {len(chunks)}")
                                        for i, chunk in enumerate(chunks[:5]):
                                            st.text_area(f"Chunk {i+1}", chunk.get('content', '')[:300], height=100)
                        else:
                            st.info("No documents found")
                            
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
            else:
                st.warning("Please enter a file name")
    
    else:
        doc_id = st.number_input("Document ID", min_value=1, value=1)
        
        if st.button("Search", key="sql_search_id"):
            with st.spinner("Searching..."):
                try:
                    doc = supabase_client.search_by_document_id(doc_id)
                    
                    if doc:
                        st.success(f"Found document: {doc.get('file_name')}")
                        st.markdown(f"**ID:** {doc['id']}")
                        st.markdown(f"**File Name:** {doc.get('file_name', 'N/A')}")
                        st.markdown(f"**Strategy:** {doc.get('strategy_used', 'N/A')}")
                        st.markdown(f"**Created:** {doc.get('created_at', 'N/A')}")
                        
                        st.subheader("Chunks")
                        chunks = supabase_client.get_chunks_by_document(doc_id)
                        st.write(f"Total chunks: {len(chunks)}")
                        
                        for i, chunk in enumerate(chunks):
                            with st.expander(f"Chunk {i+1}"):
                                st.text(chunk.get('content', '')[:500])
                    else:
                        st.info("Document not found")
                        
                except Exception as e:
                    st.error(f"Error: {str(e)}")

with st.sidebar:
    st.header("📋 Documents")
    
    if st.button("🔄 Refresh List"):
        st.rerun()
    
    try:
        docs = supabase_client.get_all_documents(limit=20)
        
        if docs:
            for doc in docs:
                st.markdown(f"**{doc.get('file_name', 'Unknown')}**")
                st.caption(f"ID: {doc['id']} | Strategy: {doc.get('strategy_used', 'N/A')}")
                st.divider()
        else:
            st.info("No documents yet")
    except Exception as e:
        st.error(f"Error loading documents: {str(e)}")

st.markdown("---")
st.caption(f"{settings.APP_NAME} v{settings.APP_VERSION}")
