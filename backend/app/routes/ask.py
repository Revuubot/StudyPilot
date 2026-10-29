"""
RAG question-answering route.
"""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import APILog, User, UserEvent
from app.schemas import AskRequest, AskResponse, Citation
from app.services import generate_answer_with_citations, retrieve_with_citations

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["ask"])


@router.post(
    "/ask",
    response_model=AskResponse,
    summary="Ask a question about your notes (RAG)",
)
async def ask_question(
    body: AskRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Answer a question using RAG over the user's study notes.

    Pipeline: embed query → pgvector similarity search → Gemini
    generation with inline citations.

    Args:
        body: Contains the query string.
        user: The authenticated user (injected).
        db: Database session (injected).

    Returns:
        Generated answer with inline citations and latency.

    Raises:
        HTTPException 500: If the RAG pipeline fails.
    """
    start = time.perf_counter()

    try:
        # 1. Retrieve relevant chunks
        retrieved = await retrieve_with_citations(db, body.query, user.id, top_k=5)

        # 2. Generate answer with citations
        answer, raw_citations = await generate_answer_with_citations(body.query, retrieved)
    except Exception as exc:
        logger.error("RAG pipeline failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Question answering failed: {str(exc)}")

    elapsed_ms = (time.perf_counter() - start) * 1000

    # 3. Build citation response objects
    citations = [
        Citation(
            source_id=c["source_id"],
            source_title=c["source_title"],
            source_type=c["source_type"],
            chunk_text=c["chunk_text"],
            relevance_score=c["relevance_score"],
            source_url=c.get("source_url"),
        )
        for c in raw_citations
    ]

    # 4. Record analytics event
    event = UserEvent(
        user_id=user.id,
        event_type="ask",
        resource_id=None,
        time_saved_minutes=2.0,  # estimated time saved vs manual search
    )
    db.add(event)

    # 5. API log
    api_log = APILog(
        user_id=user.id,
        endpoint="/api/ask",
        method="POST",
        response_time_ms=elapsed_ms,
        status_code=200,
    )
    db.add(api_log)

    logger.info("RAG answer generated in %.0f ms (%d citations)", elapsed_ms, len(citations))

    return AskResponse(
        answer=answer,
        citations=citations,
        latency_ms=round(elapsed_ms, 1),
    )
