"""
Summarisation routes: YouTube and PDF → structured study notes.
"""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import Summary, User, UserEvent, APILog, AsyncTask
from app.schemas import SummariseResponse, StructuredNotes, YouTubeSummariseRequest
from app.services import (
    estimate_time_saved,
    extract_pdf_text,
    extract_youtube_transcript,
    summarise_text,
)
from tasks import generate_embeddings_batch, transcribe_with_whisper

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/summarise", tags=["summarise"])


@router.post(
    "/youtube",
    response_model=SummariseResponse,
    summary="Summarise a YouTube video into structured notes",
)
async def summarise_youtube(
    body: YouTubeSummariseRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Extract transcript from a YouTube video and generate structured notes.

    Pipeline: URL → transcript extraction → Gemini summarisation →
    embedding storage → time-saved event.

    Args:
        body: Contains the YouTube URL.
        user: The authenticated user (injected).
        db: Database session (injected).

    Returns:
        Structured notes with topic, key concepts, detailed notes, and TL;DR.

    Raises:
        HTTPException 400: If the URL is invalid or transcript unavailable.
        HTTPException 500: If summarisation fails.
    """
    start = time.perf_counter()

    # 1. Extract transcript
    try:
        transcript, title = extract_youtube_transcript(body.url)
    except Exception as exc:
        logger.warning("Transcript extraction failed, triggering Whisper fallback: %s", exc)
        
        # Trigger Whisper via Celery
        try:
            task_record = AsyncTask(
                user_id=user.id,
                task_type="whisper_transcribe",
                input_data=body.url,
                status="pending",
            )
            db.add(task_record)
            await db.flush()
            
            celery_task = transcribe_with_whisper.delay(body.url, user.id, task_record.id)
            task_record.celery_task_id = celery_task.id
            
            return {
                "summary_id": "async_task_" + task_record.id,
                "title": "Transcription in progress...",
                "source": "youtube",
                "notes": {
                    "topic": "Task Started",
                    "tldr": "We are transcribing this video using Whisper. This may take a few minutes. Please check your dashboard later.",
                    "key_concepts": "",
                    "detailed_notes": f"Task ID: {task_record.id}"
                },
                "time_saved_minutes": 0,
                "created_at": task_record.created_at,
            }
        except Exception as celery_exc:
            logger.error("Failed to trigger Whisper task: %s", celery_exc)
            raise HTTPException(
                status_code=500,
                detail="Transcription failed and fallback could not be started."
            )

    # 2. Summarise with Gemini
    try:
        notes = await summarise_text(transcript)
    except Exception as exc:
        logger.error("Summarisation failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Summarisation failed: {str(exc)}")

    # 3. Estimate time saved
    time_saved = estimate_time_saved(len(transcript))

    # 4. Persist summary
    summary = Summary(
        user_id=user.id,
        title=notes.get("topic", title),
        source="youtube",
        source_url=body.url,
        raw_content=transcript,
        topic=notes["topic"],
        key_concepts=notes["key_concepts"],
        detailed_notes=notes["detailed_notes"],
        tldr=notes["tldr"],
    )
    db.add(summary)
    await db.flush()
    await db.refresh(summary)

    # 5. Offload embedding generation to Celery
    try:
        # Create a task record for tracking
        task_record = AsyncTask(
            user_id=user.id,
            task_type="batch_embed",
            input_data=summary.id,
            status="pending",
        )
        db.add(task_record)
        await db.flush()
        
        # Trigger Celery
        celery_task = generate_embeddings_batch.delay([summary.id], task_record.id)
        task_record.celery_task_id = celery_task.id
    except Exception as exc:
        logger.error("Failed to trigger embedding task: %s", exc)

    # 6. Record analytics event
    event = UserEvent(
        user_id=user.id,
        event_type="summarise",
        resource_id=summary.id,
        time_saved_minutes=time_saved,
    )
    db.add(event)

    # 7. Record API log
    elapsed_ms = (time.perf_counter() - start) * 1000
    api_log = APILog(
        user_id=user.id,
        endpoint="/api/summarise/youtube",
        method="POST",
        response_time_ms=elapsed_ms,
        status_code=200,
    )
    db.add(api_log)

    logger.info("YouTube summary created: %s (%.0f ms)", summary.id, elapsed_ms)

    return SummariseResponse(
        summary_id=summary.id,
        title=summary.title,
        source="youtube",
        source_url=body.url,
        notes=StructuredNotes(**notes),
        time_saved_minutes=time_saved,
        created_at=summary.created_at,
    )


@router.post(
    "/pdf",
    response_model=SummariseResponse,
    summary="Summarise an uploaded PDF into structured notes",
)
async def summarise_pdf(
    file: UploadFile = File(..., description="PDF file to summarise"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a PDF, extract text, and generate structured study notes.

    Pipeline: PDF upload → text extraction → Gemini summarisation →
    embedding storage → time-saved event.

    Args:
        file: The uploaded PDF file.
        user: The authenticated user (injected).
        db: Database session (injected).

    Returns:
        Structured notes with topic, key concepts, detailed notes, and TL;DR.

    Raises:
        HTTPException 400: If the file is not a valid PDF or is empty.
        HTTPException 500: If summarisation fails.
    """
    start = time.perf_counter()

    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    if len(file_bytes) > 50 * 1024 * 1024:  # 50 MB limit
        raise HTTPException(status_code=400, detail="File too large (max 50 MB)")

    # 1. Extract text from PDF
    try:
        text_content, title = extract_pdf_text(file_bytes)
    except Exception as exc:
        logger.error("PDF extraction failed: %s", exc)
        raise HTTPException(status_code=400, detail=f"Could not extract text from PDF: {str(exc)}")

    if not text_content.strip():
        raise HTTPException(status_code=400, detail="No text found in PDF (scanned/image-only PDFs are not supported)")

    # 2. Summarise
    try:
        notes = await summarise_text(text_content)
    except Exception as exc:
        logger.error("Summarisation failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Summarisation failed: {str(exc)}")

    # 3. Estimate time saved
    time_saved = estimate_time_saved(len(text_content))

    # 4. Persist
    summary = Summary(
        user_id=user.id,
        title=notes.get("topic", title),
        source="pdf",
        source_url=None,
        raw_content=text_content,
        topic=notes["topic"],
        key_concepts=notes["key_concepts"],
        detailed_notes=notes["detailed_notes"],
        tldr=notes["tldr"],
    )
    db.add(summary)
    await db.flush()
    await db.refresh(summary)

    # 5. Offload embedding generation to Celery
    try:
        task_record = AsyncTask(
            user_id=user.id,
            task_type="batch_embed",
            input_data=summary.id,
            status="pending",
        )
        db.add(task_record)
        await db.flush()
        
        celery_task = generate_embeddings_batch.delay([summary.id], task_record.id)
        task_record.celery_task_id = celery_task.id
    except Exception as exc:
        logger.error("Failed to trigger embedding task: %s", exc)

    # 6. Record analytics event
    event = UserEvent(
        user_id=user.id,
        event_type="summarise",
        resource_id=summary.id,
        time_saved_minutes=time_saved,
    )
    db.add(event)

    # 7. API log
    elapsed_ms = (time.perf_counter() - start) * 1000
    api_log = APILog(
        user_id=user.id,
        endpoint="/api/summarise/pdf",
        method="POST",
        response_time_ms=elapsed_ms,
        status_code=200,
    )
    db.add(api_log)

    logger.info("PDF summary created: %s (%.0f ms)", summary.id, elapsed_ms)

    return SummariseResponse(
        summary_id=summary.id,
        title=summary.title,
        source="pdf",
        source_url=None,
        notes=StructuredNotes(**notes),
        time_saved_minutes=time_saved,
        created_at=summary.created_at,
    )
