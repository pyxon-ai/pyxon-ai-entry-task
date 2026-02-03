from typing import List, Optional

from sqlalchemy.orm import Session, joinedload

from src.pyxon.storage.database import models, schemas
from src.pyxon.storage.database.database import SessionLocal


class DocumentRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_document(self, doc: schemas.DocumentCreate) -> models.Document:
        db_doc = models.Document(**doc.model_dump())
        self.db.add(db_doc)
        self.db.commit()
        self.db.refresh(db_doc)
        return db_doc

    def get_document_with_chunks(self, doc_id: str) -> Optional[models.Document]:
        return (
            self.db.query(models.Document)
            .options(joinedload(models.Document.chunks))
            .filter(models.Document.id == doc_id)
            .first()
        )

    def add_chunks(
        self, doc_id: str, chunks: List[schemas.ChunkCreate]
    ) -> List[models.Chunk]:
        db_chunks = []
        for chunk_data in chunks:
            db_chunk = models.Chunk(
                doc_id=doc_id,
                chunk_index=chunk_data.chunk_index,
                chunk_text=chunk_data.chunk_text,
            )
            self.db.add(db_chunk)
            db_chunks.append(db_chunk)

        doc = (
            self.db.query(models.Document).filter(models.Document.id == doc_id).first()
        )
        if doc:
            doc.total_chunks = len(chunks)

        self.db.commit()
        for chunk in db_chunks:
            self.db.refresh(chunk)
        return db_chunks


class SQLStore:
    def save_document(self, doc: schemas.DocumentCreate) -> str:
        session = SessionLocal()
        try:
            repo = DocumentRepository(session)
            db_doc = repo.create_document(doc)
            return str(db_doc.id)
        finally:
            session.close()

    def save_chunks(self, doc_id: str, chunks: List[schemas.ChunkCreate]) -> None:
        session = SessionLocal()
        try:
            repo = DocumentRepository(session)
            repo.add_chunks(doc_id, chunks)
        finally:
            session.close()

    def get_document(self, doc_id: str) -> Optional[schemas.DocumentWithChunks]:
        session = SessionLocal()
        try:
            repo = DocumentRepository(session)
            db_doc = repo.get_document_with_chunks(doc_id)
            if db_doc:
                return schemas.DocumentWithChunks.model_validate(db_doc)
            return None
        finally:
            session.close()
