import os
import re
import docx
from PyPDF2 import PdfReader
from sentence_transformers import SentenceTransformer

from document_classifier import classify_document
from dynamic_chunker import dynamic_chunk_text

# -----------------------------
# دوال قراءة الملفات
# -----------------------------
def read_pdf(file_path):
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text

def read_docx(file_path):
    doc = docx.Document(file_path)
    text = "\n".join([para.text for para in doc.paragraphs])
    return text

def read_txt(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()
    return text

def read_file(file_path):
    ext = file_path.split('.')[-1].lower()
    if ext == "pdf":
        return read_pdf(file_path)
    elif ext == "docx":
        return read_docx(file_path)
    elif ext == "txt":
        return read_txt(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")

# -----------------------------
# Preprocessing عربي
# -----------------------------
def preprocess_arabic(text):
    # إزالة الأحرف الإنجليزية والأرقام فقط، لا تمس الحركات
    text = re.sub(r'[A-Za-z]', '', text)
    text = re.sub(r'\d+', '', text)
    text = ' '.join(line.strip() for line in text.splitlines() if line.strip())
    return text

# -----------------------------
# Fixed Chunking
# -----------------------------
def fixed_chunk_text(text, chunk_size=1000, overlap=100):
    chunks = []
    start = 0
    length = len(text)
    while start < length:
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append({"title": "بدون عنوان", "text": chunk.strip()})
        start += chunk_size - overlap
    return chunks

# -----------------------------
# قراءة الملفات ومعالجتها
# -----------------------------
data_folder = "Data"
all_texts = []

for filename in os.listdir(data_folder):
    file_path = os.path.join(data_folder, filename)
    try:
        raw_text = read_file(file_path)
        clean_text = preprocess_arabic(raw_text)
        if clean_text:
            all_texts.append({"filename": filename, "text": clean_text})
            print(f"{filename} processed | length: {len(clean_text)}")
    except Exception as e:
        print(f"Error processing {filename}: {e}")

# -----------------------------
# Chunking + Document Classification
# -----------------------------
all_chunks = []

for item in all_texts:
    filename = item["filename"]
    text = item["text"]

    # تصنيف المستند
    doc_info = classify_document(text)

    # اختيار استراتيجية التقسيم
    if doc_info.get("chunking_strategy") == "dynamic":
        chunks = dynamic_chunk_text(text)
    else:
        chunks = fixed_chunk_text(text)

    # إضافة كل chunk صالحة
    for i, c in enumerate(chunks):
        chunk_text = c["text"] if isinstance(c, dict) else c
        chunk_title = c.get("title", "بدون عنوان") if isinstance(c, dict) else "بدون عنوان"

        if not chunk_text.strip():
            continue

        all_chunks.append({
            "filename": filename,
            "chunk_id": i,
            "chunk_text": chunk_text.strip(),
            "chunk_title": chunk_title.strip(),
            "chunking_strategy": doc_info.get("chunking_strategy", "fixed"),
            "document_type": doc_info.get("document_type", "unknown")
        })

print(f"\nTotal valid chunks: {len(all_chunks)}")

# -----------------------------
# إنشاء embeddings لكل chunk
# -----------------------------
model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

for chunk in all_chunks:
    text = chunk.get("chunk_text", "")
    if isinstance(text, str) and text.strip():
        chunk["embedding"] = model.encode(text)
    else:
        chunk["embedding"] = None

# optional: تعداد الـ chunks الفارغة
empty_chunks = [c for c in all_chunks if c.get("embedding") is None]
print(f"Chunks without embedding (skipped): {len(empty_chunks)}")

# -----------------------------
# معاينة أول chunk
# -----------------------------
if all_chunks:
    first_chunk = all_chunks[0]
    print("\n--- First Chunk Preview ---")
    print(first_chunk["chunk_text"][:300])
    print("\nEmbedding size:" if first_chunk["embedding"] is not None else "\nEmbedding is None")
    if first_chunk["embedding"] is not None:
        print(len(first_chunk["embedding"]))
