"""Database connection management."""

import os
from typing import Optional
import asyncpg
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool
from src.config.settings import settings


Base = declarative_base()


class DatabaseManager:
    """Manages database connections and sessions."""

    def __init__(self):
        self.engine = None
        self.async_engine = None
        self.SessionLocal = None
        self.AsyncSessionLocal = None

    def init_db(self):
        """Initialize database engine and session factory."""
        try:
            # Sync engine (PostgreSQL)
            self.engine = create_engine(
                settings.database_url.replace("postgresql://", "postgresql+psycopg2://"),
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=20,
            )
            # Validate connection early
            with self.engine.connect() as _:
                pass

            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine,
            )

            # Async engine (PostgreSQL)
            async_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
            self.async_engine = create_async_engine(
                async_url,
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=20,
            )
            self.AsyncSessionLocal = sessionmaker(
                self.async_engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
        except Exception:
            # Fallback to SQLite for local/dev environments
            self.engine = create_engine(
                "sqlite+pysqlite:///:memory:",
                pool_pre_ping=True,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine,
            )
            self.async_engine = None
            self.AsyncSessionLocal = None
        # Ensure tables exist for the active engine
        try:
            self.create_tables()
        except Exception:
            # Ignore table creation errors here; specific calls can handle
            pass

    async def init_pgvector(self):
        """Initialize pgvector extension."""
        if not self.async_engine:
            return
        async with self.async_engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.commit()

    def create_tables(self):
        """Create all database tables."""
        from src.database.models import DocumentModel, ChunkModel
        try:
            Base.metadata.create_all(bind=self.engine)
        except Exception:
            # Fallback to SQLite if creating tables fails (e.g., bad credentials)
            self.engine = create_engine(
                "sqlite+pysqlite:///:memory:",
                pool_pre_ping=True,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine,
            )
            Base.metadata.create_all(bind=self.engine)

    def drop_tables(self):
        """Drop all database tables."""
        Base.metadata.drop_all(bind=self.engine)

    def get_session(self):
        """Get a synchronous database session."""
        if self.SessionLocal is None:
            self.init_db()
        try:
            self.create_tables()
        except Exception:
            pass
        return self.SessionLocal()

    async def get_async_session(self):
        """Get an asynchronous database session."""
        if not self.AsyncSessionLocal:
            return
        async with self.AsyncSessionLocal() as session:
            yield session


# Global database manager instance
db_manager = DatabaseManager()
