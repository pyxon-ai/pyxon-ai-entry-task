from langchain_core.prompts import FewShotPromptTemplate, PromptTemplate
from langsmith import Client

client = Client()


GENERATION_PROMPT = client.pull_prompt("langchain-ai/retrieval-qa-chat")
# REFLECTION 

_reflection_prompt_template = """
You are a retrieval evaluator assessing document sufficiency for answering the original question.

ORIGINAL QUESTION: {original_q}

QUERY PROGRESSION (Original → Rewrites):
{queries_history}

LESSONS FROM PREVIOUS ATTEMPTS (Do NOT repeat these mistakes):
{previous_critiques}

CURRENT RETRIEVAL CONFIG:
- top_k: {current_top_k}
- metadata_filter: {current_filter}
- iteration: {iteration_count}

CURRENTLY RETRIEVED DOCUMENTS:
{current_docs_summary}

EVALUATION RULES:
1. Check if retrieved documents contain answer to original question (not keywords, but actual information)
2. Analyze why previous attempts failed based on critique history - adjust strategy accordingly
3. If previous critique said "too narrow", broaden search; if "irrelevant docs", increase similarity threshold or use filter

DECISION LOGIC:
- should_continue=false: Only if documents clearly contain sufficient, relevant information to answer fully
- should_continue=true: If documents are missing info and cannot rely on to answer original question

OUTPUT STRICT JSON:
{{
    "critique": "One short message explaining what's missing or why docs are sufficient, referencing specific doc IDs if relevant",
    "should_continue": true or false,
    "top_k": integer 1-20,
    "filter": null or {{"document_id": "uuid-string-here"}}
}}

JSON OUTPUT:
"""

REFLECTION_PROMPT = PromptTemplate(
    input_variables=[
        "original_q",
        "queries_history",
        "previous_critiques",
        "current_docs_summary",
        "current_top_k",
        "current_filter",
        "iteration_count"
    ],
    template=_reflection_prompt_template
)


# QUERY REWRITING 

query_rewrite_examples = [
    {
        "original_question": "What are the safety protocols?",
        "critique": "The answer only mentions protective equipment but misses storage and emergency procedures. Need more comprehensive information.",
        "previous_queries": "safety protocols",
        "new_query": "safety protocols hazardous materials storage emergency procedures protective equipment",
    },
    {
        "original_question": "Who is the CEO of TechCorp?",
        "critique": "No documents found. The query might be too specific. Try broader search.",
        "previous_queries": "CEO TechCorp",
        "new_query": "TechCorp leadership executive team CEO management",
    },
    {
        "original_question": "ما هي متطلبات رخصة القيادة؟",
        "critique": "No relevant Arabic documents found. Need to search with more context.",
        "previous_queries": "متطلبات رخصة القيادة",
        "new_query": "رخصة القيادة الأردن شروط متطلبات مستندات إجراءات",
    },
]

QUERY_REWRITE_EXAMPLE_TEMPLATE = """Original Question: {original_question}
Critique: {critique}
Previous Queries: {previous_queries}
New Query: {new_query}
---"""

QUERY_REWRITE_PROMPT = FewShotPromptTemplate(
    examples=query_rewrite_examples,
    example_prompt=PromptTemplate(
        input_variables=[
            "original_question",
            "critique",
            "previous_queries",
            "new_query",
        ],
        template=QUERY_REWRITE_EXAMPLE_TEMPLATE,
    ),
    prefix="""You are a query rewriting expert. Your job is to reformulate search queries based on critique feedback.

Guidelines:
- Expand queries with related terms and synonyms
- Add context if the original query was too narrow
- Maintain the original language (Arabic queries stay in Arabic)
- Consider previous failed queries to avoid repetition
- Make queries more specific if too broad, or broader if too specific

Here are some examples:
""",
    suffix="""Now rewrite this query:

Original Question: {original_question}
Latest Critique: {latest_critique}
Previous Queries: {previous_queries}
Previous Critiques: {previous_critiques}

Generate a new search query that addresses the critique. Return ONLY the new query, nothing else.

New Query:""",
    input_variables=[
        "original_question",
        "latest_critique",
        "previous_queries",
        "previous_critiques",
    ],
)
