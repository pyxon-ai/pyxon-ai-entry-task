# -----------------------------
# store_chunks.py
# تخزين الـ chunks + embeddings في Chroma (Vector DB) و SQLite
# -----------------------------

import numpy as np
import chromadb
from chromadb.config import Settings
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import declarative_base, sessionmaker

# -----------------------------
# افتراض أن all_chunks موجودة
# كل عنصر في all_chunks يحتوي على:
# - filename
# - chunk_id
# - chunk_text
# - embedding (numpy array)
# -----------------------------

try:
    from main import all_chunks
except ImportError:
    raise ImportError("الملف main.py يجب أن يكون موجود ويحتوي على all_chunks")

# -----------------------------
# إعداد Chroma (Vector DB)
# -----------------------------
client = chromadb.Client()


try:
    collection = client.get_collection("documents")
except chromadb.errors.NotFoundError:
    collection = client.create_collection("documents")

print("Collection ready:", collection.name)


# -----------------------------
# إعداد SQLite (SQL DB) باستخدام SQLAlchemy
# -----------------------------
Base = declarative_base()

class ChunkMeta(Base):
    __tablename__ = "chunks"
    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String)
    chunk_id = Column(Integer)
    chunk_title = Column(String)  
    length = Column(Integer)
    text = Column(Text)

engine = create_engine("sqlite:///chunks.db")
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

# -----------------------------
# تخزين كل chunk في Chroma و SQLite
# -----------------------------
for chunk in all_chunks:
    # تخزين في Vector DB
    collection.add(
    documents=[chunk["chunk_text"]],
    metadatas=[{
        "filename": chunk["filename"],
        "chunk_id": chunk["chunk_id"],
        "chunk_title": chunk.get("chunk_title", "بدون عنوان")
    }],
    ids=[f"{chunk['filename']}_{chunk['chunk_id']}"],
    embeddings=[chunk["embedding"].tolist()]
)


    # تخزين في SQLite
    meta = ChunkMeta(
    filename=chunk["filename"],
    chunk_id=chunk["chunk_id"],
    chunk_title=chunk.get("chunk_title", "بدون عنوان"),
    length=len(chunk["chunk_text"]),
    text=chunk["chunk_text"]
)
session.add(meta)


session.commit()
print(f"\nStored {len(all_chunks)} chunks in Vector DB and SQLite successfully.")
