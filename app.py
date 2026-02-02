import streamlit as st
import os
import sqlite3
import pandas as pd
from dotenv import load_dotenv
from document_processor import DocumentProcessor
from database_manager import DatabaseManager

# LangChain Libraries (LCEL)
from langchain_openai import ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

# Load settings from .env file
load_dotenv()

st.set_page_config(page_title="Pyxon AI - Document Parser", layout="wide", page_icon="📄")

# Verify API (OpenAI)
if not os.getenv("OPENAI_API_KEY"):
    st.error(" Error: OPENAI_API_KEY not found. Please add it to the .env file.")
    st.stop()

# Note: FAISS was selected as the Vector DB to ensure full compatibility with Windows
processor = DocumentProcessor()
db_mgr = DatabaseManager()
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# Helper function to merge retrieved texts (Crucial for RAG)
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

with st.sidebar:
    st.title("⚙️ Settings & Upload")
    st.markdown("Upload your files to train the system on them (PDF, DOCX, TXT)")
    
    uploaded_file = st.file_uploader("Choose a file", type=['pdf', 'docx', 'txt'])
    
    if uploaded_file:
        with st.spinner("Processing and smart chunking in progress..."):
            temp_path = f"temp_{uploaded_file.name}"
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # Execute processing: load -> split -> hybrid storage
            chunks = processor.load_and_split(temp_path)
            db_mgr.save_to_vector_db(chunks)  # Store in FAISS
            db_mgr.save_metadata(uploaded_file.name, len(chunks))  # Store in SQL
            
            os.remove(temp_path)
            st.success(f"✅ Saved successfully! The file was split into {len(chunks)} chunks.")

    st.divider()
    st.subheader("📊 SQL Database (Metadata)")
    if st.button("Show uploaded files log"):
        conn = sqlite3.connect(db_mgr.db_name)
        df = pd.read_sql_query(
            "SELECT * FROM docs_metadata ORDER BY upload_date DESC",
            conn
        )
        st.dataframe(df)
        conn.close()

# Main Page (The RAG Engine)
st.title("📄 AI-Powered Document Parser")
st.markdown(
    "An intelligent system for reading documents and retrieving information, "
    "with full Arabic language support."
)

query = st.text_input(
    " Ask any question about the document content:",
    placeholder="e.g., What are the main points in the document?"
)

index_file = os.path.join(db_mgr.vector_db_path, "index.faiss")

if query:
    if not os.path.exists(index_file):
        st.warning("⚠️ Please upload a file first to activate the search engine.")
    else:
        with st.spinner("Extracting the answer from the documents..."):
            try:
                vectorstore = FAISS.load_local(
                    db_mgr.vector_db_path,
                    db_mgr.embeddings,
                    allow_dangerous_deserialization=True
                )
                retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

                # prompt for the AI (Arabic-focused)
                template = """You are an intelligent assistant specialized in document analysis.
Use only the following context chunks to answer the user's question.
If the answer is not present in the context, clearly state that you do not have the information.
Maintain accuracy when reproducing words, especially names and fully-diacritized terms.

Context:
{context}

Question: {question}

Answer (in Modern Standard Arabic):"""
                
                prompt = ChatPromptTemplate.from_template(template)
                rag_chain = (
                    {"context": retriever | format_docs, "question": RunnablePassthrough()}
                    | prompt
                    | llm
                    | StrOutputParser()
                )

                response = rag_chain.invoke(query)
                
                st.markdown("### 💡 Generated Answer:")
                st.success(response)
                
                # Show sources - a key evaluation requirement
                with st.expander("📚 Retrieved Sources (Context Chunks)"):
                    docs = retriever.invoke(query)
                    for i, doc in enumerate(docs):
                        st.write(f"**Chunk {i+1}:**")
                        st.text(doc.page_content)
                        st.divider()

            except Exception as e:
                st.error(f" A technical error occurred: {e}")

st.divider()
st.caption("Submitted for Pyxon AI Technical Task | Built with LangChain, FAISS, and Streamlit")
