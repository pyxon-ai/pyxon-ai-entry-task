"""Route corpus-metadata questions to SQL; send everything else to retrieval.

A question goes to SQL only when *every* content word in it belongs to the metadata
vocabulary below (documents, chunks, counts, languages, file types, chunking strategy,
diacritics). Any other word ("coffee", "Zephyr", "marketing") means the user is asking
about document *content*, so the question goes to RAG. This removes the false positives
of first-match regex rules ("What is the marketing strategy for Zephyr?" is not about the
parser's chunking strategy).

The parsed intent (target, count vs list, filters, document scope) is turned into a
parameterised SELECT; values are never pasted into SQL text.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .text import content_tokens


def _vocab(words: str) -> set[str]:
    return set(content_tokens(words))


# --- vocabulary (normalized + light-stemmed exactly like query tokens) -----------------
DOC_WORDS = _vocab("document documents doc docs file files مستند مستندات المستندات ملف ملفات الملفات وثيقة وثائق الوثائق")
CHUNK_WORDS = _vocab("chunk chunks passage passages مقطع مقاطع المقاطع جزء أجزاء الأجزاء")
COUNT_WORDS = _vocab("how many count number total كم عدد")
LIST_WORDS = _vocab("list show which what all display اعرض أعرض جميع")
FILLER = _vocab(
    "indexed stored uploaded available exist there are is in the of with have has contain contains "
    "per each by language languages type types written use used uses using applied chosen selected picked "
    "استخدمت المستخدمة المفهرسة المخزنة الموجودة المتوفرة لدي لديك "
    "مكتوبة المكتوبة لغة اللغة نوع"
)
ARABIC = _vocab("arabic عربي عربية العربية بالعربية")
ENGLISH = _vocab("english إنجليزي إنجليزية الإنجليزية انجليزي الانجليزية بالإنجليزية")
MIXED = _vocab("mixed bilingual مختلط ثنائية")
DIACRITICS = _vocab("diacritics diacritic harakat tashkeel vocalized vowelled تشكيل التشكيل بالتشكيل حركات الحركات مشكولة")
FILETYPES = {"pdf": "pdf", "docx": "docx", "doc": "doc", "txt": "txt", "text": "txt", "word": "docx"}
STRATEGY = _vocab("strategy strategies chunking استراتيجية الاستراتيجية التقسيم تقسيم طريقة")
FIXED = _vocab("fixed ثابت الثابت")
DYNAMIC = _vocab("dynamic ديناميكي الديناميكي")

KNOWN = (DOC_WORDS | CHUNK_WORDS | COUNT_WORDS | LIST_WORDS | FILLER | ARABIC | ENGLISH | MIXED
         | DIACRITICS | set(FILETYPES) | STRATEGY | FIXED | DYNAMIC)


@dataclass
class StructuredQuery:
    sql: str
    params: list = field(default_factory=list)
    kind: str = "list"  # list | count | strategy | chunks


def parse(question: str, doc_ids: list[int] | None = None) -> StructuredQuery | None:
    tokens = set(content_tokens(question))
    if not tokens or tokens - KNOWN:
        return None  # mentions something other than corpus metadata -> content question

    about_chunks = bool(tokens & CHUNK_WORDS)
    about_docs = bool(tokens & DOC_WORDS)
    about_strategy = bool(tokens & STRATEGY) and ("chunking" in tokens or bool(tokens & _vocab("التقسيم تقسيم"))
                                                   or about_docs or bool(tokens & (FIXED | DYNAMIC)))
    if not (about_chunks or about_docs or about_strategy):
        return None
    counting = bool(tokens & COUNT_WORDS)

    where, params = [], []
    langs = [code for code, words in (("ar", ARABIC), ("en", ENGLISH), ("mixed", MIXED)) if tokens & words]
    if langs:
        # a bilingual document counts as both Arabic and English
        if "ar" in langs or "en" in langs:
            langs.append("mixed")
        langs = sorted(set(langs))
        where.append(f"d.language IN ({','.join('?' * len(langs))})")
        params += langs
    if tokens & DIACRITICS:
        where.append("d.has_diacritics = 1")
    types = sorted({FILETYPES[t] for t in tokens if t in FILETYPES})
    if types:
        where.append(f"d.file_type IN ({','.join('?' * len(types))})")
        params += types
    if tokens & FIXED and not tokens & DYNAMIC:
        where.append("d.strategy = ?")
        params.append("fixed")
    elif tokens & DYNAMIC and not tokens & FIXED:
        where.append("d.strategy = ?")
        params.append("dynamic")
    if doc_ids:
        where.append(f"d.id IN ({','.join('?' * len(doc_ids))})")
        params += [int(i) for i in doc_ids]
    cond = (" WHERE " + " AND ".join(where)) if where else ""

    if about_chunks:
        join = "FROM documents d JOIN chunks c ON c.document_id = d.id AND c.level = 0"
        if counting and not about_docs:
            return StructuredQuery(f"SELECT COUNT(c.id) AS chunks {join}{cond}", params, "count")
        return StructuredQuery(
            f"SELECT d.filename, d.strategy, COUNT(c.id) AS chunks {join}{cond} GROUP BY d.id ORDER BY d.id",
            params, "chunks")
    if about_strategy and not counting:
        return StructuredQuery(
            f"SELECT d.filename, d.strategy, d.strategy_reasons FROM documents d{cond} ORDER BY d.id", params, "strategy")
    if counting:
        return StructuredQuery(f"SELECT COUNT(*) AS documents FROM documents d{cond}", params, "count")
    return StructuredQuery(
        "SELECT d.id, d.filename, d.file_type, d.language, d.has_diacritics, d.strategy, d.doc_type "
        f"FROM documents d{cond} ORDER BY d.id", params, "list")
