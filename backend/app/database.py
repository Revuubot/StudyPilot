"""
Async SQLAlchemy engine, session factory, and Base declarative class.

Provides:
- ``engine``  – the async engine bound to DATABASE_URL
- ``AsyncSessionLocal`` – a session-maker for request-scoped sessions
- ``Base``    – declarative base for ORM models
- ``get_db``  – FastAPI dependency that yields a session per request
- ``init_db`` – creates the pgvector extension and all tables on startup
"""

from __future__ import annotations

import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Engine ────────────────────────────────────────────────────────────────────
engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=300,
)

# ── Session factory ───────────────────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── Declarative Base ─────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


# ── Dependency ────────────────────────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that provides a database session.

    The session is automatically closed after the request completes,
    regardless of whether an exception occurred.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ── Bootstrap ─────────────────────────────────────────────────────────────────
async def init_db() -> None:
    """Create the pgvector extension and all database tables.

    Called once at application startup. Safe to call multiple times –
    ``CREATE EXTENSION IF NOT EXISTS`` and ``create_all`` are idempotent.
    """
    async with engine.begin() as conn:
        # Enable pgvector extension
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        logger.info("pgvector extension enabled")

        # Import models so Base.metadata is populated
        import app.models  # noqa: F401

        await conn.run_sync(Base.metadata.create_all)
        logger.info("All database tables created / verified")
