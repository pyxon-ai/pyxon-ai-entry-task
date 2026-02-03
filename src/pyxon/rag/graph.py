# src.pyxon.rag.graph

from langgraph.graph import END, START, StateGraph

from src.config import Settings
from src.pyxon.rag.nodes import (generate_node, reflect_node, rerank_node,
                                 retrieve_node, rewrite_query_node)
from src.pyxon.rag.state import AgentState

flow = StateGraph(AgentState)


def route_after_reflect(state: AgentState) -> str:
    if state["should_continue"] and state["iteration"] <= Settings.MAX_RAG_ITERATIONS:
        return "rewrite_query_node"
    else:
        return "generate_node"


flow.add_node("retrieve_node", retrieve_node)
flow.add_node("rerank_node", rerank_node)
flow.add_node("reflect_node", reflect_node)
flow.add_node("rewrite_query_node", rewrite_query_node)
flow.add_node("generate_node", generate_node)

flow.add_edge(START, "retrieve_node")
flow.add_edge("retrieve_node", "rerank_node")
flow.add_edge("rerank_node", "reflect_node")
flow.add_conditional_edges(
    "reflect_node",
    route_after_reflect,
    {"rewrite_query_node": "rewrite_query_node", "generate_node": "generate_node"},
)
flow.add_edge("rewrite_query_node", "retrieve_node")
flow.add_edge("generate_node", END)

app = flow.compile()
