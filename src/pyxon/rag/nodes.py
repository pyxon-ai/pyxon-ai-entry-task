# src.pyxon.rag.nodes
import json
import logging
from uuid import UUID

from langchain_core.messages import AIMessage, HumanMessage
from langchain_groq import ChatGroq

from src.pyxon.rag.schemas import ReflectionDecision
from src.pyxon.rag.utils import format_docs_summary, format_previous_critiques, format_queries_history
from src.pyxon.retrieval.reranker import CrossEncoderReranker
from src.pyxon.storage.vs import VectorStore

from src.config import Settings
from src.pyxon.rag.prompts import (
    GENERATION_PROMPT,
    QUERY_REWRITE_PROMPT,
    REFLECTION_PROMPT,
)
from src.pyxon.rag.state import AgentState

logger = logging.getLogger(__name__)


_vs = VectorStore()._vs
_reranker = CrossEncoderReranker()
_llm = ChatGroq(model=Settings.LLM_MODEL_NAME, api_key=Settings.GROQ_API_KEY)

def retrieve_node(state: AgentState) -> AgentState:
    state['iteration'] += 1
    current_iteration = state['iteration']
    
    logger.info(f"[Retrieve] Starting iteration {current_iteration}")
    
    if len(state["queries"]) == 0:
        original_query = state['messages'][-1].content
        state["queries"].append(original_query)
        logger.info(f"[Retrieve] Initial query: '{original_query[:100]}...'")

    query = state["queries"][-1]
    similarity_threshold = Settings.SIMILARITY_THRESHOLD
    metadata_filter = state.get("metadata_filter")
    
    logger.debug(f"[Retrieve] Query: '{query[:100]}...' | Threshold: {similarity_threshold} | Filter: {metadata_filter}")

    search_kwargs = {"k": 20, "similarity_score_threshold": similarity_threshold}
    if metadata_filter:
        search_kwargs["filter"] = metadata_filter
        logger.info(f"[Retrieve] Applying metadata filter: {metadata_filter}")

    try:
        retrieved_docs = _vs.search(
            query=query, 
            search_type="similarity_score_threshold",
            search_kwargs=search_kwargs
        )
        state["retrieved_docs"] = retrieved_docs
        logger.info(f"[Retrieve] Retrieved {len(retrieved_docs)} documents (Iteration {current_iteration})")
        
        if retrieved_docs:
            top_score = getattr(retrieved_docs[0], 'metadata', {}).get('score', 'N/A')
            logger.debug(f"[Retrieve] Top doc score: {top_score}")
            
    except Exception as e:
        logger.error(f"[Retrieve] Failed to retrieve documents: {str(e)}")
        state["retrieved_docs"] = []
    
    return state

def rerank_node(state: AgentState) -> AgentState:
    query = state["queries"][-1]
    top_k = state.get("top_k", Settings.TOP_K)
    docs_count = len(state.get("retrieved_docs", []))
    
    logger.info(f"[Rerank] Reranking {docs_count} documents for query: '{query[:80]}...' | TopK: {top_k}")

    try:
        reranked_docs = _reranker.rerank(
            query=query, 
            documents=state["retrieved_docs"], 
            top_k=top_k
        )
        state["reranked_docs"] = reranked_docs
        logger.info(f"[Rerank] Reranked to top {len(reranked_docs)} documents")
        
        if reranked_docs:
            scores = [getattr(doc, 'metadata', {}).get('score', 0) for doc in reranked_docs[:3]]
            logger.debug(f"[Rerank] Top 3 scores: {scores}")
            
    except Exception as e:
        logger.error(f"[Rerank] Reranking failed: {str(e)}")
        state["reranked_docs"] = state["retrieved_docs"][:top_k]  

    return state

def reflect_node(state: AgentState) -> AgentState:
    queries = state.get("queries", [])
    critiques = state.get("critiques", [])
    docs = state.get("reranked_docs", [])
    current_top_k = state.get("top_k", Settings.TOP_K)
    current_filter = state.get("metadata_filter", None)
    iteration = state['iteration']
    
    logger.info(f"[Reflect] Reflection iteration {iteration} | Queries so far: {len(queries)} | Docs to evaluate: {len(docs)}")
    
    prompt_input = {
        "original_q": state['messages'][-1].content,
        "queries_history": format_queries_history(queries),
        "previous_critiques": format_previous_critiques(critiques),
        "current_docs_summary": format_docs_summary(docs),
        "current_top_k": current_top_k,
        "current_filter": json.dumps(current_filter) if current_filter else "null",
        "iteration_count": iteration
    }

    try:
        llm = _llm.with_structured_output(ReflectionDecision)
        chain = REFLECTION_PROMPT | llm 
        response: ReflectionDecision = chain.invoke(prompt_input)
        
        logger.info(f"[Reflect] Decision: continue={response.should_continue} | New top_k: {response.top_k}")
        logger.debug(f"[Reflect] Critique: {response.critique[:200]}...")

        if response.should_continue:
            state["critiques"] = critiques + [response.critique]
            state["should_continue"] = True
            state["top_k"] = response.top_k
            
            logger.info(f"[Reflect] Adding critique #{len(state['critiques'])}. Will continue to rewrite.")
            
            # Handle filter update
            if response.filter and response.filter.get("document_id"):
                try:
                    UUID(response.filter["document_id"])
                    state["metadata_filter"] = response.filter
                    logger.info(f"[Reflect] Updated metadata filter: {response.filter}")
                except ValueError as e:
                    logger.warning(f"[Reflect] Invalid UUID in filter, keeping current filter. Error: {e}")
                    state["metadata_filter"] = current_filter
            else:
                state["metadata_filter"] = None
                if response.filter:
                    logger.debug(f"[Reflect] Filter provided but no document_id, ignoring")
        else:
            state["should_continue"] = False
            logger.info(f"[Reflect] Stopping loop. Final iteration: {iteration}")
            
    except Exception as e:
        logger.error(f"[Reflect] Reflection failed: {str(e)}. Stopping to prevent infinite loop.")
        state["should_continue"] = False
    
    return state

def rewrite_query_node(state: AgentState) -> AgentState:
    original_question = state['messages'][-1].content
    latest_critique = state["critiques"][-1]
    iteration = state['iteration']

    logger.info(f"[Rewrite] Rewriting query (Iteration {iteration}) based on critique")
    logger.debug(f"[Rewrite] Original: '{original_question[:100]}...'")
    logger.debug(f"[Rewrite] Critique: '{latest_critique[:150]}...'")

    previous_queries = format_queries_history(state["queries"])
    previous_critiques = format_previous_critiques(state["critiques"])

    rewrite_prompt = QUERY_REWRITE_PROMPT.format(
        original_question=original_question,
        latest_critique=latest_critique,
        previous_queries=previous_queries,
        previous_critiques=previous_critiques,
    )

    try:
        new_query = _llm.invoke(rewrite_prompt).content.strip()
        state["queries"].append(new_query)
        logger.info(f"[Rewrite] New query generated ({len(state['queries'])} total): '{new_query[:100]}...'")
    except Exception as e:
        logger.error(f"[Rewrite] Query rewrite failed: {str(e)}. Keeping original query.")
        state["queries"].append(original_question)  # Fallback

    return state

def generate_node(state: AgentState) -> AgentState:
    question = state["messages"][-1].content if state["messages"] else ""
    iteration = state['iteration']
    docs_count = len(state.get("reranked_docs", []))

    logger.info(f"[Generate] Generating answer (Iteration {iteration}) using {docs_count} documents")

    if state["reranked_docs"]:
        context = format_docs_summary(state['reranked_docs'])
        logger.debug(f"[Generate] Context length: {len(context)} chars from {docs_count} docs")
    else:
        context = "No relevant documents found."
        logger.warning(f"[Generate] No documents available for generation!")

    prompt = GENERATION_PROMPT.format(context=context, input=question)
    
    try:
        answer = _llm.invoke(prompt).content
        state["messages"].append(AIMessage(content=answer))
        state["answer"] = answer
        logger.info(f"[Generate] Answer generated ({len(answer)} chars)")
        logger.debug(f"[Generate] Answer preview: '{answer[:200]}...'")
    except Exception as e:
        logger.error(f"[Generate] Generation failed: {str(e)}")
        error_msg = "Sorry, I encountered an error generating the response."
        state["messages"].append(AIMessage(content=error_msg))
        state["answer"] = error_msg

    return state