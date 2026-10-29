"""
Pydantic request / response schemas for every API endpoint.

Naming convention:
- ``*Request``   – inbound payload
- ``*Response``  – outbound payload
- ``*Base``      – shared fields
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field


# ══════════════════════════════════════════════════════════════════════════════
# Auth
# ══════════════════════════════════════════════════════════════════════════════
class RegisterRequest(BaseModel):
    """Body for POST /api/auth/register."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class LoginRequest(BaseModel):
    """Body for POST /api/auth/login."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """JWT token returned on login / register."""
    access_token: str
    token_type: str = "bearer"
    user_id: str


# ══════════════════════════════════════════════════════════════════════════════
# Summarise
# ══════════════════════════════════════════════════════════════════════════════
class YouTubeSummariseRequest(BaseModel):
    """Body for POST /api/summarise/youtube."""
    url: str = Field(..., description="Full YouTube video URL")


class StructuredNotes(BaseModel):
    """The four-section notes format produced by Gemini."""
    topic: str = ""
    key_concepts: str = ""
    detailed_notes: str = ""
    tldr: str = ""


class SummariseResponse(BaseModel):
    """Response for both YouTube and PDF summarisation."""
    summary_id: str
    title: str
    source: str
    source_url: Optional[str] = None
    notes: StructuredNotes
    time_saved_minutes: float
    created_at: datetime


# ══════════════════════════════════════════════════════════════════════════════
# Ask (RAG)
# ══════════════════════════════════════════════════════════════════════════════
class AskRequest(BaseModel):
    """Body for POST /api/ask."""
    query: str = Field(..., min_length=3, max_length=2000)


class Citation(BaseModel):
    """A single source citation from the RAG pipeline."""
    source_id: str
    source_title: str
    source_type: str  # "youtube" | "pdf"
    chunk_text: str
    relevance_score: float
    source_url: Optional[str] = None


class AskResponse(BaseModel):
    """Response for POST /api/ask."""
    answer: str
    citations: List[Citation]
    latency_ms: float


# ══════════════════════════════════════════════════════════════════════════════
# Search
# ══════════════════════════════════════════════════════════════════════════════
class SearchResult(BaseModel):
    """A single semantic search hit."""
    summary_id: str
    title: str
    source: str
    chunk_text: str
    relevance_score: float
    source_url: Optional[str] = None


class SearchResponse(BaseModel):
    """Response for GET /api/search."""
    query: str
    results: List[SearchResult]
    total: int


# ══════════════════════════════════════════════════════════════════════════════
# Analytics
# ══════════════════════════════════════════════════════════════════════════════
class DailyTrend(BaseModel):
    """One day's aggregated metrics."""
    date: str
    summaries: int = 0
    questions: int = 0
    searches: int = 0
    time_saved: float = 0.0


class AnalyticsResponse(BaseModel):
    """Response for GET /api/analytics/dashboard."""
    total_summaries: int
    total_questions: int
    total_searches: int
    total_time_saved_minutes: float
    daily_trends: List[DailyTrend]
    top_notes: List[Dict[str, Any]]


# ══════════════════════════════════════════════════════════════════════════════
# Metrics / Evaluation
# ══════════════════════════════════════════════════════════════════════════════
class EvaluationMetrics(BaseModel):
    """System-level quality metrics."""
    avg_retrieval_latency_ms: float
    avg_generation_latency_ms: float
    total_queries: int
    avg_citations_per_answer: float
    embedding_count: int


# ══════════════════════════════════════════════════════════════════════════════
# Tasks
# ══════════════════════════════════════════════════════════════════════════════
class TaskStatusResponse(BaseModel):
    """Response for GET /api/tasks/{task_id}."""
    task_id: str
    task_type: str
    status: str
    result: Optional[str] = None
    created_at: datetime


# ══════════════════════════════════════════════════════════════════════════════
# Generic
# ══════════════════════════════════════════════════════════════════════════════
class ErrorResponse(BaseModel):
    """Standard error envelope."""
    detail: str


class HealthResponse(BaseModel):
    """Response for GET /health."""
    status: str = "ok"
    version: str = "1.0.0"
