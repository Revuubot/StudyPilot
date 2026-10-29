"""
Celery worker tasks for long-running background jobs.

Tasks:
- transcribe_with_whisper  – Whisper fallback for videos without captions
- generate_embeddings_batch – Batch-embed notes
- send_notification_email  – Email delivery
"""

from __future__ import annotations

import json
import logging
import os
import smtplib
import tempfile
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from celery import Celery
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger(__name__)

# ── Celery app ────────────────────────────────────────────────────────────────
CELERY_BROKER = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1")

celery_app = Celery(
    "studypilot",
    broker=CELERY_BROKER,
    backend=CELERY_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=600,   # 10 minutes
    task_time_limit=900,        # 15 minutes hard limit
)

# ── Sync database session for Celery (cannot use async in Celery workers) ────
DATABASE_URL_SYNC = os.getenv(
    "DATABASE_URL_SYNC",
    "postgresql://studypilot:studypilot@postgres:5432/studypilot",
)
sync_engine = create_engine(DATABASE_URL_SYNC, pool_pre_ping=True)
SyncSession = sessionmaker(bind=sync_engine)


def _get_sync_db() -> Session:
    """Create a new synchronous database session for use in Celery tasks."""
    return SyncSession()


# ══════════════════════════════════════════════════════════════════════════════
# Task 1: Whisper Transcription
# ══════════════════════════════════════════════════════════════════════════════

@celery_app.task(bind=True, name="tasks.transcribe_with_whisper", max_retries=2)
def transcribe_with_whisper(self, video_url: str, user_id: str, task_record_id: str) -> dict:
    """Download a YouTube video and transcribe it using OpenAI Whisper.

    This is the fallback path when ``youtube-transcript-api`` fails
    (e.g. no captions available).

    Args:
        video_url: Full YouTube URL.
        user_id: The requesting user's ID.
        task_record_id: The AsyncTask row ID for status tracking.

    Returns:
        A dict with ``transcript`` and ``title`` keys.
    """
    db = _get_sync_db()

    try:
        # Update task status → running
        _update_task_status(db, task_record_id, "running")

        # 1. Download audio using yt-dlp
        import yt_dlp

        with tempfile.TemporaryDirectory() as tmp_dir:
            audio_path = os.path.join(tmp_dir, "audio.mp3")
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": os.path.join(tmp_dir, "audio.%(ext)s"),
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "128",
                    }
                ],
                "quiet": True,
                "no_warnings": True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=True)
                title = info.get("title", "Untitled Video")

            # 2. Transcribe with OpenAI Whisper API
            import openai

            openai_key = os.getenv("OPENAI_API_KEY", "")
            if not openai_key:
                raise ValueError("OPENAI_API_KEY is not set")

            client = openai.OpenAI(api_key=openai_key)

            # Find the downloaded audio file
            audio_files = [f for f in os.listdir(tmp_dir) if f.endswith((".mp3", ".m4a", ".wav"))]
            if not audio_files:
                raise FileNotFoundError("No audio file found after download")

            actual_path = os.path.join(tmp_dir, audio_files[0])

            with open(actual_path, "rb") as audio_file:
                transcript_response = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="verbose_json",
                    timestamp_granularities=["segment"],
                )

            # 3. Format transcript with timestamps
            segments = []
            if hasattr(transcript_response, "segments") and transcript_response.segments:
                for seg in transcript_response.segments:
                    start_min = int(seg["start"] // 60)
                    start_sec = int(seg["start"] % 60)
                    timestamp = f"[{start_min:02d}:{start_sec:02d}]"
                    segments.append(f"{timestamp} {seg['text'].strip()}")
            else:
                segments.append(transcript_response.text)

            transcript = "\n".join(segments)

            # 4. Update task status → done
            result_data = json.dumps({"transcript": transcript, "title": title})
            _update_task_status(db, task_record_id, "done", result=result_data)

            logger.info("Whisper transcription complete for %s (%d chars)", video_url, len(transcript))
            return {"transcript": transcript, "title": title}

    except Exception as exc:
        logger.error("Whisper transcription failed: %s", exc)
        _update_task_status(db, task_record_id, "failed", result=str(exc))
        raise self.retry(exc=exc, countdown=30)
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════════════
# Task 2: Batch Embedding Generation
# ══════════════════════════════════════════════════════════════════════════════

@celery_app.task(bind=True, name="tasks.generate_embeddings_batch", max_retries=1)
def generate_embeddings_batch(self, note_ids: list[str], task_record_id: str) -> dict:
    """Generate embeddings for a batch of summary notes.

    Iterates over each summary, chunks the raw content, embeds each
    chunk, and stores the vectors in ``note_embeddings``.

    Args:
        note_ids: List of Summary IDs to embed.
        task_record_id: The AsyncTask row ID for status tracking.

    Returns:
        A dict with ``embedded_count`` and ``total_chunks`` keys.
    """
    import google.generativeai as genai

    from app.models import NoteEmbedding, Summary
    from app.services import chunk_text

    db = _get_sync_db()

    try:
        _update_task_status(db, task_record_id, "running")

        gemini_key = os.getenv("GEMINI_API_KEY", "")
        if not gemini_key:
            raise ValueError("GEMINI_API_KEY is not set")

        genai.configure(api_key=gemini_key)

        total_chunks = 0
        embedded_count = 0

        for note_id in note_ids:
            summary = db.query(Summary).filter(Summary.id == note_id).first()
            if not summary or not summary.raw_content:
                continue

            chunks = chunk_text(summary.raw_content)
            for idx, chunk in enumerate(chunks):
                try:
                    result = genai.embed_content(
                        model="models/gemini-embedding-001",
                        content=chunk,
                        task_type="retrieval_document",
                    )
                    embedding_row = NoteEmbedding(
                        summary_id=note_id,
                        chunk_text=chunk,
                        chunk_index=idx,
                        embedding=result["embedding"],
                    )
                    db.add(embedding_row)
                    embedded_count += 1
                except Exception as exc:
                    logger.error("Failed to embed chunk %d of note %s: %s", idx, note_id, exc)

                total_chunks += 1

            db.commit()

        result_data = json.dumps({"embedded_count": embedded_count, "total_chunks": total_chunks})
        _update_task_status(db, task_record_id, "done", result=result_data)

        logger.info("Batch embedding complete: %d/%d chunks", embedded_count, total_chunks)
        return {"embedded_count": embedded_count, "total_chunks": total_chunks}

    except Exception as exc:
        logger.error("Batch embedding failed: %s", exc)
        _update_task_status(db, task_record_id, "failed", result=str(exc))
        raise self.retry(exc=exc, countdown=60)
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════════════
# Task 3: Notification Email
# ══════════════════════════════════════════════════════════════════════════════

@celery_app.task(bind=True, name="tasks.send_notification_email", max_retries=3)
def send_notification_email(
    self,
    user_id: str,
    subject: str,
    message: str,
    task_record_id: str,
) -> dict:
    """Send a notification email to a user.

    Uses SMTP configuration from environment variables.

    Args:
        user_id: The user's ID (used to look up their email).
        subject: Email subject line.
        message: Email body (plain text).
        task_record_id: The AsyncTask row ID for status tracking.

    Returns:
        A dict with ``sent_to`` key.
    """
    from app.models import User

    db = _get_sync_db()

    try:
        _update_task_status(db, task_record_id, "running")

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")

        smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER", "")
        smtp_password = os.getenv("SMTP_PASSWORD", "")

        if not smtp_user or not smtp_password:
            logger.warning("SMTP not configured – skipping email to %s", user.email)
            _update_task_status(db, task_record_id, "done", result="SMTP not configured")
            return {"sent_to": user.email, "skipped": True}

        msg = MIMEMultipart()
        msg["From"] = smtp_user
        msg["To"] = user.email
        msg["Subject"] = f"[StudyPilot] {subject}"
        msg.attach(MIMEText(message, "plain"))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, user.email, msg.as_string())

        _update_task_status(db, task_record_id, "done", result=f"Sent to {user.email}")
        logger.info("Email sent to %s: %s", user.email, subject)
        return {"sent_to": user.email}

    except Exception as exc:
        logger.error("Email sending failed: %s", exc)
        _update_task_status(db, task_record_id, "failed", result=str(exc))
        raise self.retry(exc=exc, countdown=30)
    finally:
        db.close()


# ══════════════════════════════════════════════════════════════════════════════
# Helper
# ══════════════════════════════════════════════════════════════════════════════

def _update_task_status(db: Session, task_id: str, status: str, result: str | None = None) -> None:
    """Update an AsyncTask row's status and optional result.

    Args:
        db: Synchronous database session.
        task_id: The AsyncTask primary key.
        status: New status string (``running``, ``done``, ``failed``).
        result: Optional result payload.
    """
    from app.models import AsyncTask

    task = db.query(AsyncTask).filter(AsyncTask.id == task_id).first()
    if task:
        task.status = status
        if result is not None:
            task.result = result
        db.commit()
