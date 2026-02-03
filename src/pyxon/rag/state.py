# src.pyxon.rag.state

from operator import add
from langchain_core.messages import BaseMessage
from typing import Annotated, Any, Dict, List, Optional, TypedDict
from langchain_core.documents import Document


class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add]
    queries: Annotated[List[str], add]
    critiques: Annotated[List[str], add]
    iteration: int
    should_continue: bool
    retrieved_docs: List[Document]
    reranked_docs: List[Document]
    top_k: int
    metadata_filter: Optional[Dict[str, Any]]
    answer: str