import re


# -------------------------------------------------
# Arabic Normalization
# -------------------------------------------------
def normalize_arabic(text: str) -> str:
    """
    Normalize Arabic text by removing diacritics (harakat)
    to allow fair comparison between texts.
    """
    if not text:
        return ""

    arabic_diacritics = re.compile(
        r"""
        ّ    | # Tashdid
        َ    | # Fatha
        ً    | # Tanwin Fath
        ُ    | # Damma
        ٌ    | # Tanwin Damm
        ِ    | # Kasra
        ٍ    | # Tanwin Kasr
        ْ    | # Sukun
        ـ      # Tatwil
        """,
        re.VERBOSE,
    )

    return re.sub(arabic_diacritics, "", text)


# -------------------------------------------------
# Precision / Recall Metrics
# -------------------------------------------------
def precision_at_k(retrieved_ids, relevant_ids, k):
    """
    Precision@k = (number of relevant retrieved documents in top k) / k
    """
    if k == 0:
        return 0.0

    retrieved_k = retrieved_ids[:k]
    relevant_retrieved = len(set(retrieved_k) & set(relevant_ids))
    return relevant_retrieved / k


def recall_at_k(retrieved_ids, relevant_ids, k):
    """
    Recall@k = (number of relevant retrieved documents in top k) / total relevant documents
    """
    if not relevant_ids:
        return 0.0

    retrieved_k = retrieved_ids[:k]
    relevant_retrieved = len(set(retrieved_k) & set(relevant_ids))
    return relevant_retrieved / len(relevant_ids)


# -------------------------------------------------
# Keyword-based Retrieval Accuracy (Arabic-aware)
# -------------------------------------------------
def retrieval_accuracy(retrieved_text: str, expected_keywords: list) -> float:
    """
    Measures how many expected keywords appear in the retrieved text.
    Arabic diacritics are normalized before comparison.
    """
    if not expected_keywords or not retrieved_text:
        return 0.0

    text_norm = normalize_arabic(retrieved_text)

    hits = 0
    for keyword in expected_keywords:
        keyword_norm = normalize_arabic(keyword)
        if keyword_norm in text_norm:
            hits += 1

    return hits / len(expected_keywords)


# -------------------------------------------------
# Chunk Quality Metric
# -------------------------------------------------
def chunk_quality(chunk_text: str) -> float:
    """
    Heuristic metric to evaluate chunk quality based on:
    - length (not too short, not too long)
    - basic semantic completeness
    """
    if not chunk_text:
        return 0.0

    length_score = min(len(chunk_text) / 300, 1.0)
    word_count = len(chunk_text.split())
    sentence_score = 1.0 if word_count >= 10 else 0.5

    return round((length_score + sentence_score) / 2, 2)