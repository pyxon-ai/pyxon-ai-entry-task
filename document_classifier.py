# -----------------------------
# Document Type Classification (Arabic)
# -----------------------------

import re

# -----------------------------
# دوال مساعدة
# -----------------------------
def is_quranic_text(text: str) -> bool:
    quran_markers = [
        "بسم الله الرحمن الرحيم",
        "قال الله تعالى",
        "سورة",
        "آية",
        "الذين آمنوا",
        "يوم الدين"
    ]
    return any(marker in text for marker in quran_markers)


def is_academic_paper(text: str) -> bool:
    academic_markers = [
        "الملخص",
        "Abstract",
        "منهجية",
        "الدراسة",
        "النتائج",
        "المراجع",
        "الخاتمة"
    ]
    return any(marker in text for marker in academic_markers)


def is_magazine_article(text: str) -> bool:
    magazine_markers = [
        "مجلة",
        "العدد",
        "ISSN",
        "تحرير",
        "بقلم",
        "افتتاحية"
    ]
    return any(marker in text for marker in magazine_markers)


def estimate_document_length(text: str) -> int:
    return len(text.split())

# -----------------------------
# التصنيف الرئيسي
# -----------------------------
def classify_document(text: str) -> dict:
    length = estimate_document_length(text)

    if is_quranic_text(text):
        return {
            "document_type": "religious_text",
            "chunking_strategy": "dynamic",
            "reason": "نص ديني يتطلب احترام البنية والمعنى"
        }

    if is_academic_paper(text):
        return {
            "document_type": "academic_paper",
            "chunking_strategy": "dynamic",
            "reason": "بحث أكاديمي يحتوي أقسام واضحة"
        }

    if is_magazine_article(text):
        return {
            "document_type": "magazine_article",
            "chunking_strategy": "fixed",
            "reason": "مقال شبه موحد الطول"
        }

    if length > 5000:
        return {
            "document_type": "long_document",
            "chunking_strategy": "dynamic",
            "reason": "مستند طويل مع محتوى متغير"
        }

    return {
        "document_type": "generic_text",
        "chunking_strategy": "fixed",
        "reason": "نص عام بدون بنية واضحة"
    }

# -----------------------------
# اختبار سريع
# -----------------------------
if __name__ == "__main__":
    sample_text = """
    بسم الله الرحمن الرحيم الحمد لله رب العالمين
    """
    result = classify_document(sample_text)
    print(result)
