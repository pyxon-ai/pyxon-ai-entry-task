import os
import sqlite3
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# --- 1. إعداد قاعدة بيانات SQL (طلب الشركة) ---
def init_sql_db():
    conn = sqlite3.connect('pyxon_data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS docs (id INTEGER PRIMARY KEY, content TEXT)''')
    conn.commit()
    return conn

# --- 2. دالة معالجة أنواع الملفات المختلفة ---
def load_any_file(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.pdf':
        return PyPDFLoader(file_path).load()
    elif ext == '.docx':
        return Docx2txtLoader(file_path).load()
    elif ext == '.txt':
        return TextLoader(file_path).load()
    else:
        raise ValueError("نوع الملف غير مدعوم حالياً")

# --- 3. المحرك الرئيسي للمشروع ---
class PyxonEngine:
    def __init__(self, file_path):
        self.file_path = file_path
        self.sql_conn = init_sql_db()
        
        # إعداد النماذج (دعم العربية والحركات)
        self.embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
        
        # معالجة الملف
        docs = load_any_file(file_path)
        
        # التقطيع الذكي (Intelligent Chunking)
        splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
        self.chunks = splitter.split_documents(docs)
        
        # تخزين في SQL (لحفظ نسخة نصية)
        cursor = self.sql_conn.cursor()
        for chunk in self.chunks:
            cursor.execute("INSERT INTO docs (content) VALUES (?)", (chunk.page_content,))
        self.sql_conn.commit()
        
        # بناء الـ Vector DB (Chroma)
        self.vector_db = Chroma.from_documents(self.chunks, self.embeddings, persist_directory="./db_pyxon_final")
        print(f"[✔] تم معالجة {len(self.chunks)} قطعة نصية وتخزينها في SQL و Vector DB.")

    def search(self, query):
        return self.vector_db.similarity_search(query, k=2)

# --- واجهة التشغيل ---
if __name__ == "__main__":
    print("=== Pyxon AI: Junior Engineer Task - Develop by Eng. Osama ===")
    FILE_TO_PROCESS = "text.pdf" # يمكنك تغيير الصيغة لـ .docx أو .txt
    
    if os.path.exists(FILE_TO_PROCESS):
        engine = PyxonEngine(FILE_TO_PROCESS)
        
        while True:
            q = input("\nاسأل النظام عن محتوى الملف (أو 'خروج'): ")
            if q.lower() in ['خروج', 'exit']: break
            
            results = engine.search(q)
            print(f"\n[النتائج المسترجعة]:\n" + "-"*30)
            for i, res in enumerate(results):
                print(f"{i+1}. {res.page_content}\n")
    else:
        print("يرجى التأكد من وجود ملف المشروع.")