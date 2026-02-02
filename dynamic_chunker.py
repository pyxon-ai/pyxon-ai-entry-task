# -----------------------------
# Dynamic Chunking for Arabic Documents
# -----------------------------

import re

# -----------------------------
# كشف العناوين العربية
# -----------------------------
ARABIC_HEADINGS = [
    "الملخص",
    "مقدمة",
    "تمهيد",
    "الفصل",
    "المبحث",
    "المطلب",
    "الخاتمة",
    "النتائج",
    "المراجع"
]

def is_heading(line: str) -> bool:
    line = line.strip()
    if len(line) > 80:
        return False

    for h in ARABIC_HEADINGS:
        if line.startswith(h):
            return True

    # أرقام الفصول: الفصل الأول، الفصل الثاني...
    if re.match(r"(الفصل|المبحث)\s+\w+", line):
        return True

    return False

# -----------------------------
# Dynamic Chunking
# -----------------------------
def dynamic_chunk_text(text: str, max_chunk_size=1000):
    lines = text.split("\n")
    chunks = []

    current_chunk = ""
    current_title = "بدون عنوان"

    for line in lines:
        if is_heading(line):
            # حفظ الـ chunk السابق
            if current_chunk.strip():
                chunks.append({
                    "title": current_title,
                    "text": f"Title: {current_title}\n\n{current_chunk.strip()}"
                })

            # بدء chunk جديد
            current_title = line.strip()
            current_chunk = ""
        else:
            current_chunk += line + " "

            # حماية من الطول الزائد
            if len(current_chunk) > max_chunk_size:
                chunks.append({
                    "title": current_title,
                    "text": f"Title: {current_title}\n\n{current_chunk.strip()}"
                })
                current_chunk = ""

    # آخر chunk
    if current_chunk.strip():
        chunks.append({
            "title": current_title,
            "text": f"Title: {current_title}\n\n{current_chunk.strip()}"
        })

    return chunks


# -----------------------------
# اختبار
# -----------------------------
if __name__ == "__main__":
    sample_text = """
    مقدمة
    هذا بحث يتحدث عن الذكاء الاصطناعي.

    الفصل الأول
    تعريف الذكاء الاصطناعي وتاريخه.

    الفصل الثاني
    تطبيقات الذكاء الاصطناعي في الطب.
    """

    chunks = dynamic_chunk_text(sample_text)
    for c in chunks:
        print("TITLE:", c["title"])
        print("TEXT:", c["text"][:100])
        print("-" * 40)
