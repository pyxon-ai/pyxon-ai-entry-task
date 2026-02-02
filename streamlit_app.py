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
    
    col1, col2 = st.columns(2)
    
    with col1:
        content_filter = st.text_input("Content contains", placeholder="Search text...")
        file_name_filter = st.text_input("File name", placeholder="e.g., report.pdf")
    
    with col2:
        strategy_filter = st.selectbox("Strategy", ["All", "FIXED", "SEMANTIC"])
        doc_id_filter = st.number_input("Document ID", min_value=0, value=0)
    
    sql_limit = st.slider("Number of results", 1, 100, 20, key="sql_limit")
    
    if st.button("Search", key="sql_search"):
        with st.spinner("Searching..."):
            try:
                results = supabase_client.advanced_search(
                    content=content_filter if content_filter else None,
                    file_name=file_name_filter if file_name_filter else None,
                    strategy=strategy_filter if strategy_filter != "All" else None,
                    document_id=doc_id_filter if doc_id_filter > 0 else None,
                    limit=sql_limit
                )
                
                if results:
                    st.success(f"Found {len(results)} results")
                    
                    for i, result in enumerate(results):
                        doc_info = result.get('documents', {})
                        with st.expander(f"📄 Chunk {i+1} | Doc: {doc_info.get('file_name', 'Unknown')}"):
                            st.markdown(f"**Content:**\n{result.get('content', '')[:500]}...")
                            st.markdown(f"**Document ID:** {result.get('document_id')}")
                            st.markdown(f"**Strategy:** {doc_info.get('strategy_used', 'N/A')}")
                else:
                    st.info("No results found")
                    
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
