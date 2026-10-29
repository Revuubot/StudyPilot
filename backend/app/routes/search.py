"""
Semantic search route across all user notes.
"""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import APILog, User, UserEvent
from app.schemas import SearchResponse, SearchResult
from app.services import retrieve_with_citations

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["search"])


@router.get(
    "/search",
    response_model=SearchResponse,
    summary="Semantic search across your notes",
)
async def semantic_search(
    q: str = Query(..., min_length=2, max_length=500, description="Search query"),
    top_k: int = Query(10, ge=1, le=50, description="Number of results"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Search across all of the user's study notes using semantic similarity.

    Embeds the query using Gemini and performs a pgvector cosine
    similarity search.

    Args:
        q: The search query string.
        top_k: Maximum results to return.
        user: The authenticated user (injected).
        db: Database session (injected).

    Returns:
        Ranked search results with relevance scores.

    Raises:
        HTTPException 500: If the search pipeline fails.
    """
    start = time.perf_counter()

    try:
        retrieved = await retrieve_with_citations(db, q, user.id, top_k=top_k)
    except Exception as exc:
        logger.error("Semantic search failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(exc)}")

    elapsed_ms = (time.perf_counter() - start) * 1000

    results = [
        SearchResult(
            summary_id=r["summary_id"],
            title=r["title"],
            source=r["source"],
            chunk_text=r["chunk_text"][:500],
            relevance_score=r["relevance_score"],
            source_url=r.get("source_url"),
        )
        for r in retrieved
    ]

    # Record analytics
    event = UserEvent(
        user_id=user.id,
        event_type="search",
        resource_id=None,
        time_saved_minutes=1.0,
    )
    db.add(event)

    api_log = APILog(
        user_id=user.id,
        endpoint="/api/search",
        method="GET",
        response_time_ms=elapsed_ms,
        status_code=200,
    )
    db.add(api_log)

    logger.info("Search for '%s' returned %d results in %.0f ms", q[:50], len(results), elapsed_ms)

    return SearchResponse(
        query=q,
        results=results,
        total=len(results),
    )
