from typing import List
from langchain_core.documents import Document

def format_queries_history(queries: List[str]) -> str:
    if not queries:
        return "No queries yet"
    
    lines = []
    for i, query in enumerate(queries):
        if i == 0:
            lines.append(f"  [Original] {query}")
        else:
            lines.append(f"  [Rewrite {i}]  {query}")

    return "\n".join(lines)


def format_previous_critiques(critiques: List[str]) -> str:
    if not critiques:
        return "  First attempt - no previous feedback"
    
    lines = []
    for i, critique in enumerate(critiques, 1):
        lines.append(f"  Attempt {i}: {critique}")

    return "\n".join(lines)


def format_docs_summary(docs: List[Document]) -> str:
    if not docs:
        return "  NO DOCUMENTS RETRIEVED"
    
    lines = []
    for i, doc in enumerate(docs[:20], 1):
        content = doc.page_content
        meta = doc.metadata
        doc_id = meta.get('document_id', 'unknown')
        
        lines.append(f"  Doc{i}[ID:{doc_id}]: {content}...")
    
    return "\n".join(lines)
