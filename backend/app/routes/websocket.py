"""
WebSocket endpoint for streaming RAG answers.

Clients connect to ``/ws/ask``, send a JSON message with ``token`` and
``query``, and receive streamed answer chunks plus final citations.
"""

from __future__ import annotations

import json
import logging
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.auth import decode_token
from app.database import AsyncSessionLocal
from app.models import User, UserEvent
from app.services import generate_answer_with_citations, retrieve_with_citations

logger = logging.getLogger(__name__)
router = APIRouter(tags=["websocket"])


@router.websocket("/ws/ask")
async def websocket_ask(ws: WebSocket):
    """WebSocket endpoint for streaming RAG question answering.

    Protocol:
    1. Client sends: ``{"token": "...", "query": "..."}``
    2. Server authenticates the token.
    3. Server streams the answer in chunks:
       ``{"type": "chunk", "content": "..."}``
    4. Server sends final citations:
       ``{"type": "citations", "data": [...]}``
    5. Server sends completion:
       ``{"type": "done", "latency_ms": ...}``

    On error, the server sends ``{"type": "error", "detail": "..."}``
    and closes the connection.
    """
    await ws.accept()
    logger.info("WebSocket connection accepted")

    try:
        # 1. Receive the initial message with token + query
        raw = await ws.receive_text()
        message = json.loads(raw)
        token = message.get("token", "")
        query = message.get("query", "")

        if not token or not query:
            await ws.send_json({"type": "error", "detail": "Both 'token' and 'query' are required"})
            await ws.close()
            return

        # 2. Authenticate
        try:
            payload = decode_token(token)
            user_id = payload.get("uid")
        except Exception:
            await ws.send_json({"type": "error", "detail": "Invalid or expired token"})
            await ws.close()
            return

        # 3. Verify user exists
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if not user:
                await ws.send_json({"type": "error", "detail": "User not found"})
                await ws.close()
                return

            start = time.perf_counter()

            # 4. Retrieve relevant chunks
            await ws.send_json({"type": "status", "content": "Searching your notes..."})
            retrieved = await retrieve_with_citations(db, query, user_id, top_k=5)

            if not retrieved:
                await ws.send_json({
                    "type": "chunk",
                    "content": "I don't have any notes to answer from. Please summarise some content first.",
                })
                await ws.send_json({"type": "done", "latency_ms": 0})
                await ws.close()
                return

            # 5. Generate answer
            await ws.send_json({"type": "status", "content": "Generating answer..."})
            answer, raw_citations = await generate_answer_with_citations(query, retrieved)

            # 6. Stream answer in chunks (simulate streaming by splitting on sentences)
            sentences = answer.replace(". ", ".\n").split("\n")
            for sentence in sentences:
                if sentence.strip():
                    await ws.send_json({"type": "chunk", "content": sentence.strip() + " "})

            # 7. Send citations
            citations_data = [
                {
                    "source_id": c["source_id"],
                    "source_title": c["source_title"],
                    "source_type": c["source_type"],
                    "chunk_text": c["chunk_text"][:300],
                    "relevance_score": c["relevance_score"],
                    "source_url": c.get("source_url"),
                }
                for c in raw_citations
            ]
            await ws.send_json({"type": "citations", "data": citations_data})

            elapsed_ms = (time.perf_counter() - start) * 1000

            # 8. Record event
            event = UserEvent(
                user_id=user_id,
                event_type="ask",
                time_saved_minutes=2.0,
            )
            db.add(event)
            await db.commit()

            # 9. Send completion
            await ws.send_json({"type": "done", "latency_ms": round(elapsed_ms, 1)})
            logger.info("WebSocket RAG completed in %.0f ms", elapsed_ms)

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except json.JSONDecodeError:
        await ws.send_json({"type": "error", "detail": "Invalid JSON message"})
        await ws.close()
    except Exception as exc:
        logger.error("WebSocket error: %s", exc)
        try:
            await ws.send_json({"type": "error", "detail": str(exc)})
            await ws.close()
        except Exception:
            pass
