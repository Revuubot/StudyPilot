"""
SQLAlchemy ORM models for StudyPilot.

Tables:
- users            – registered users
- summaries        – generated study notes
- note_embeddings  – pgvector chunks for RAG
- user_events      – analytics events (time saved, etc.)
- api_logs         – request-level observability
- async_tasks      – Celery task tracking
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


def _utcnow() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


def _uuid() -> str:
    """Generate a new UUID4 string."""
    return str(uuid.uuid4())


# ──────────────────────────────────────────────────────────────────────────────
# User
# ──────────────────────────────────────────────────────────────────────────────
class User(Base):
    """Registered user of the platform."""

    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    summaries = relationship("Summary", back_populates="user", cascade="all, delete-orphan")
    events = relationship("UserEvent", back_populates="user", cascade="all, delete-orphan")
    api_logs = relationship("APILog", back_populates="user", cascade="all, delete-orphan")
    tasks = relationship("AsyncTask", back_populates="user", cascade="all, delete-orphan")


# ──────────────────────────────────────────────────────────────────────────────
# Summary (study notes)
# ──────────────────────────────────────────────────────────────────────────────
class Summary(Base):
    """A set of structured study notes generated from a source."""

    __tablename__ = "summaries"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    source = Column(String(50), nullable=False)  # "youtube" | "pdf"
    source_url = Column(Text, nullable=True)
    raw_content = Column(Text, nullable=False)
    topic = Column(Text, nullable=True)
    key_concepts = Column(Text, nullable=True)
    detailed_notes = Column(Text, nullable=True)
    tldr = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="summaries")
    embeddings = relationship("NoteEmbedding", back_populates="summary", cascade="all, delete-orphan")


# ──────────────────────────────────────────────────────────────────────────────
# Note Embedding (pgvector)
# ──────────────────────────────────────────────────────────────────────────────
class NoteEmbedding(Base):
    """A text chunk and its vector embedding for semantic search / RAG."""

    __tablename__ = "note_embeddings"

    id = Column(String(36), primary_key=True, default=_uuid)
    summary_id = Column(String(36), ForeignKey("summaries.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_text = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False, default=0)
    embedding = Column(Vector(768), nullable=True)  # Gemini embedding dimension
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    summary = relationship("Summary", back_populates="embeddings")

    # ivfflat index for fast cosine similarity search
    __table_args__ = (
        Index(
            "ix_note_embeddings_vector",
            embedding,
            postgresql_using="ivfflat",
            postgresql_with={"lists": 100},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )


# ──────────────────────────────────────────────────────────────────────────────
# User Event (analytics)
# ──────────────────────────────────────────────────────────────────────────────
class UserEvent(Base):
    """Tracks user activity for the analytics dashboard."""

    __tablename__ = "user_events"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)  # "summarise", "ask", "search"
    resource_id = Column(String(36), nullable=True)
    time_saved_minutes = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="events")


# ──────────────────────────────────────────────────────────────────────────────
# API Log (observability)
# ──────────────────────────────────────────────────────────────────────────────
class APILog(Base):
    """Per-request log entry for observability and cost tracking."""

    __tablename__ = "api_logs"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    endpoint = Column(String(255), nullable=False)
    method = Column(String(10), nullable=False)
    response_time_ms = Column(Float, nullable=False, default=0.0)
    status_code = Column(Integer, nullable=False, default=200)
    cost_dollars = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="api_logs")


# ──────────────────────────────────────────────────────────────────────────────
# Async Task (Celery tracking)
# ──────────────────────────────────────────────────────────────────────────────
class AsyncTask(Base):
    """Tracks background Celery tasks for status polling."""

    __tablename__ = "async_tasks"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    task_type = Column(String(50), nullable=False)  # "whisper_transcribe", "batch_embed", "email"
    input_data = Column(Text, nullable=True)
    celery_task_id = Column(String(255), nullable=True, index=True)
    status = Column(String(20), nullable=False, default="pending")  # pending | running | done | failed
    result = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="tasks")
