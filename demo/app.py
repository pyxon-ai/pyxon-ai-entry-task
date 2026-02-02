"""
Streamlit demo: upload file, run ingest, send query. Multi-file: close (×) removes file and its data.
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

import streamlit as st

from src.pipeline import run_ingest, run_rag, delete_document

st.set_page_config(page_title="Pyxon AI", layout="centered", initial_sidebar_state="collapsed")

# Data dir
(ROOT / "data").mkdir(exist_ok=True)
(ROOT / "data" / "chroma").mkdir(exist_ok=True)
(ROOT / "data" / "uploaded").mkdir(parents=True, exist_ok=True)
os.environ.setdefault("CHROMA_PATH", str(ROOT / "data" / "chroma"))
os.environ.setdefault("SQLITE_PATH", str(ROOT / "data" / "documents.db"))

# List of open files: list of {"name", "document_id", "path"}
if "open_files" not in st.session_state:
    st.session_state["open_files"] = []

# ----- Upload -----
uploaded = st.file_uploader("Upload file", type=["pdf", "docx", "doc", "txt"])

if uploaded:
    path = ROOT / "data" / "uploaded" / uploaded.name
    path.write_bytes(uploaded.getvalue())
    file_path = str(path)
    # Ingest only if not already open (avoid re-ingest on rerun)
    already = [f for f in st.session_state.get("open_files", []) if f.get("path") == file_path]
    if not already:
        with st.spinner("Ingesting..."):
            try:
                result = run_ingest(file_path)
                doc_id = result.get("document_id")
                name = Path(file_path).name
                st.session_state["open_files"] = [
                    f for f in st.session_state["open_files"]
                    if f.get("document_id") != doc_id
                ]
                st.session_state["open_files"].append({"name": name, "document_id": doc_id, "path": file_path})
            except Exception as e:
                st.error(str(e))

# ----- Open files: list with × to close -----
open_files = st.session_state.get("open_files", [])
if open_files:
    n = min(len(open_files), 10)
    cols = st.columns(n)
    for i, f in enumerate(open_files[:n]):
        with cols[i]:
            label = f.get("name", "?")
            doc_id = f.get("document_id", "")
            if st.button("× " + label, key="close_" + doc_id + "_" + str(i)):
                if doc_id:
                    try:
                        delete_document(doc_id)
                    except Exception:
                        pass
                st.session_state["open_files"] = [x for x in st.session_state["open_files"] if x.get("document_id") != doc_id]
                st.session_state.pop("rag_result", None)
                st.rerun()

# ----- Query -----
query = st.text_input("Query", placeholder="Ask a question", label_visibility="collapsed")
if st.button("Send"):
    if not query.strip():
        st.warning("Enter a question.")
    elif not open_files:
        st.warning("Upload at least one file first.")
    else:
        # When only one file is open, scope retrieval to it for better relevance
        filter_metadata = None
        if len(open_files) == 1 and open_files[0].get("document_id"):
            filter_metadata = {"document_id": open_files[0]["document_id"]}
        with st.spinner("Searching..."):
            try:
                result = run_rag(
                    query.strip(),
                    top_k=8,
                    use_graph_rag=True,
                    use_raptor=True,
                    filter_metadata=filter_metadata,
                )
                st.session_state["rag_result"] = result
            except Exception as e:
                st.error(str(e))
                st.session_state["rag_result"] = None

if st.session_state.get("rag_result"):
    r = st.session_state["rag_result"]
    chunks = r.get("chunks", [])
    st.write("**Answer:**", (r.get("answer") or "")[:500])
    st.write("**Matches:**", len(chunks))
    for i, c in enumerate(chunks[:10]):
        st.text_area("", c.get("text", ""), height=100, key=f"chunk_{i}", label_visibility="collapsed")
