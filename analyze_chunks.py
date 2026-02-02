# analyze_chunks.py
import re
from keybert import KeyBERT

try:
    from main import all_chunks
except ImportError:
    raise ImportError("main.py يجب أن يحتوي على all_chunks")

# -----------------------------
# إعداد KeyBERT (يدعم العربية)
kw_model = KeyBERT(model="paraphrase-multilingual-MiniLM-L12-v2")

# قائمة كلمات توقف بسيطة بالعربية لتحسين النتائج
arabic_stopwords = [
    "و", "في", "على", "من", "عن", "إلى", "أن", "ما", "لا", "كل",
    "هذا", "هذه", "ذلك", "تلك", "إن", "كان", "كانت", "هو", "هي"
]

# -----------------------------
# معالجة الـ chunks
for chunk in all_chunks:
    text = chunk["chunk_text"]
    processed_text = text  # الحركات محفوظة

    keywords = kw_model.extract_keywords(
        processed_text,
        keyphrase_ngram_range=(1, 2),
        stop_words=arabic_stopwords,
        top_n=5
    )

    chunk["keywords"] = [kw[0] for kw in keywords]
    chunk["topics"] = [kw[0] for kw in keywords]

# -----------------------------
# معاينة النتائج لأول 3 chunks
for chunk in all_chunks[:3]:
    print(f"Chunk {chunk['chunk_id']} ({chunk['filename']})")
    print("Title:", chunk.get("chunk_title", "بدون عنوان"))
    print("Keywords:", chunk["keywords"])
    print("-" * 40)
