"""
Core business-logic services for StudyPilot.

Every function in this module is a pure service – it has no knowledge of
HTTP or FastAPI and can be called from routes, Celery tasks, or tests.

Sections:
1. Content extraction  (YouTube transcripts, PDF text)
2. Text chunking
3. Gemini integration  (embeddings + summarisation)
4. RAG pipeline        (retrieve → generate → cite)
"""

from __future__ import annotations

import json
import logging
import math
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import google.generativeai as genai
import numpy as np
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from youtube_transcript_api import YouTubeTranscriptApi

from app.config import get_settings
from app.models import NoteEmbedding, Summary

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Configure Gemini on import ────────────────────────────────────────────────
if settings.gemini_api_key:
    genai.configure(api_key=settings.gemini_api_key)


# ══════════════════════════════════════════════════════════════════════════════
# 1.  CONTENT EXTRACTION
# ══════════════════════════════════════════════════════════════════════════════

def extract_video_id(url: str) -> str:
    """Extract the 11-character video ID from various YouTube URL formats.

    Supports:
    - https://www.youtube.com/watch?v=XXXX
    - https://youtu.be/XXXX
    - https://www.youtube.com/embed/XXXX

    Args:
        url: A YouTube URL string.

    Returns:
        The video ID.

    Raises:
        ValueError: If no valid video ID can be extracted.
    """
    patterns = [
        r"(?:youtube\.com/watch\?v=)([\w-]{11})",
        r"(?:youtu\.be/)([\w-]{11})",
        r"(?:youtube\.com/embed/)([\w-]{11})",
        r"(?:youtube\.com/v/)([\w-]{11})",
    ]
    for pat in patterns:
        match = re.search(pat, url)
        if match:
            return match.group(1)
    raise ValueError(f"Could not extract video ID from URL: {url}")


def extract_youtube_transcript(url: str) -> Tuple[str, str]:
    """Fetch the transcript (captions) for a YouTube video.

    Uses ``youtube-transcript-api`` – no API key required.

    Args:
        url: Full YouTube video URL.

    Returns:
        A tuple of ``(full_text, video_title_placeholder)``.
        The transcript text has timestamps embedded as ``[MM:SS]`` markers.

    Raises:
        ValueError: If the video ID cannot be parsed.
        Exception: If no transcript is available (triggers Whisper fallback).
    """
    video_id = extract_video_id(url)
    logger.info("Fetching transcript for video %s", video_id)

    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

    # Prefer manually-created transcripts, fall back to auto-generated
    try:
        transcript = transcript_list.find_manually_created_transcript(["en"])
    except Exception:
        transcript = transcript_list.find_generated_transcript(["en"])

    entries = transcript.fetch()
    segments: List[str] = []
    for entry in entries:
        minutes = int(entry["start"] // 60)
        seconds = int(entry["start"] % 60)
        timestamp = f"[{minutes:02d}:{seconds:02d}]"
        segments.append(f"{timestamp} {entry['text']}")

    full_text = "\n".join(segments)
    title = f"YouTube Video {video_id}"
    return full_text, title


def extract_pdf_text(file_bytes: bytes) -> Tuple[str, str]:
    """Extract all text from a PDF file.

    Uses PyMuPDF (``fitz``) for robust extraction.  Each page is
    prefixed with a ``[Page N]`` marker for citation purposes.

    Args:
        file_bytes: The raw PDF file bytes.

    Returns:
        A tuple of ``(full_text, document_title)``.
    """
    import fitz  # PyMuPDF

    doc = fitz.open(stream=file_bytes, filetype="pdf")
    title = doc.metadata.get("title", "") or "Untitled PDF"
    pages: List[str] = []

    for page_num, page in enumerate(doc, start=1):
        page_text = page.get_text("text").strip()
        if page_text:
            pages.append(f"[Page {page_num}]\n{page_text}")

    doc.close()
    full_text = "\n\n".join(pages)
    logger.info("Extracted %d pages from PDF '%s'", len(pages), title)
    return full_text, title


# ══════════════════════════════════════════════════════════════════════════════
# 2.  TEXT CHUNKING
# ══════════════════════════════════════════════════════════════════════════════

def chunk_text(text: str, max_tokens: int = 3000, overlap: int = 200) -> List[str]:
    """Split text into overlapping chunks suitable for embedding.

    Uses a simple word-based chunking strategy with configurable overlap
    to preserve context across chunk boundaries.

    Args:
        text: The full text to chunk.
        max_tokens: Maximum approximate token count per chunk (~1 token ≈ 0.75 words).
        overlap: Number of words to overlap between consecutive chunks.

    Returns:
        A list of text chunks.
    """
    words = text.split()
    # Approximate: 1 token ≈ 0.75 words → max_words ≈ max_tokens * 0.75
    max_words = int(max_tokens * 0.75)

    if len(words) <= max_words:
        return [text]

    chunks: List[str] = []
    start = 0
    while start < len(words):
        end = min(start + max_words, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        if end >= len(words):
            break
        start = end - overlap

    logger.info("Split text into %d chunks (max_tokens=%d, overlap=%d)", len(chunks), max_tokens, overlap)
    return chunks


# ══════════════════════════════════════════════════════════════════════════════
# 3.  GEMINI INTEGRATION
# ══════════════════════════════════════════════════════════════════════════════

SUMMARISE_PROMPT = """You are an expert study assistant. Given the following lecture content, 
produce structured study notes in EXACTLY this JSON format (no markdown fences, just raw JSON):

{{
  "topic": "Main topic/title of the lecture",
  "key_concepts": "Bullet-pointed list of key concepts (use \\n for line breaks)",
  "detailed_notes": "Comprehensive, well-organised notes covering all important points (use \\n for line breaks)",
  "tldr": "A concise 2-3 sentence summary"
}}

LECTURE CONTENT:
{content}

IMPORTANT: Return ONLY valid JSON, no other text."""


async def summarise_text(text_content: str) -> Dict[str, str]:
    """Generate structured study notes from raw text using Gemini 1.5 Flash.

    The response is parsed into four sections: topic, key_concepts,
    detailed_notes, and tldr.

    Args:
        text_content: The raw lecture / document text.

    Returns:
        A dict with keys ``topic``, ``key_concepts``, ``detailed_notes``, ``tldr``.

    Raises:
        ValueError: If the Gemini response cannot be parsed as JSON.
    """
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY is not configured")

    # If the text is very long, summarise the first chunk and note it's partial
    truncated = text_content[:12000] if len(text_content) > 12000 else text_content
    prompt = SUMMARISE_PROMPT.format(content=truncated)

    logger.info("Sending summarisation request to Gemini (%d chars)", len(truncated))
    model = genai.GenerativeModel("gemini-flash-latest")
    response = model.generate_content(prompt)
    raw = response.text.strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

    try:
        notes = json.loads(raw)
    except json.JSONDecodeError:
        logger.error("Failed to parse Gemini response as JSON: %s", raw[:500])
        # Fallback: treat entire response as detailed notes
        notes = {
            "topic": "Study Notes",
            "key_concepts": "",
            "detailed_notes": raw,
            "tldr": "",
        }

    return {
        "topic": notes.get("topic", "Study Notes"),
        "key_concepts": notes.get("key_concepts", ""),
        "detailed_notes": notes.get("detailed_notes", ""),
        "tldr": notes.get("tldr", ""),
    }


async def embed_text(text_content: str) -> List[float]:
    """Generate a 768-dimensional embedding vector using Gemini.

    Args:
        text_content: The text to embed.

    Returns:
        A list of 768 floats representing the embedding vector.

    Raises:
        ValueError: If the API key is missing.
    """
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY is not configured")

    result = genai.embed_content(
        model="models/gemini-embedding-001",
        content=text_content,
        task_type="retrieval_document",
    )
    embedding = result["embedding"]
    logger.debug("Generated embedding of dimension %d", len(embedding))
    return embedding


async def embed_query(query: str) -> List[float]:
    """Generate an embedding for a search/retrieval *query*.

    Uses ``task_type='retrieval_query'`` for optimal similarity matching.

    Args:
        query: The search query text.

    Returns:
        A list of 768 floats.
    """
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY is not configured")

    result = genai.embed_content(
        model="models/gemini-embedding-001",
        content=query,
        task_type="retrieval_query",
    )
    return result["embedding"]


# ══════════════════════════════════════════════════════════════════════════════
# 4.  RAG PIPELINE
# ══════════════════════════════════════════════════════════════════════════════

async def store_embeddings(
    db: AsyncSession,
    summary_id: str,
    text_content: str,
) -> int:
    """Chunk text, embed each chunk, and persist to the note_embeddings table.

    Args:
        db: The async database session.
        summary_id: The parent summary's ID.
        text_content: The full text to chunk and embed.

    Returns:
        The number of embedding rows inserted.
    """
    chunks = chunk_text(text_content)
    count = 0

    for idx, chunk in enumerate(chunks):
        try:
            vec = await embed_text(chunk)
            embedding_row = NoteEmbedding(
                summary_id=summary_id,
                chunk_text=chunk,
                chunk_index=idx,
                embedding=vec,
            )
            db.add(embedding_row)
            count += 1
        except Exception as exc:
            logger.error("Failed to embed chunk %d for summary %s: %s", idx, summary_id, exc)

    await db.flush()
    logger.info("Stored %d embeddings for summary %s", count, summary_id)
    return count


async def retrieve_with_citations(
    db: AsyncSession,
    query: str,
    user_id: str,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """Retrieve the most relevant text chunks using pgvector cosine similarity.

    Joins ``note_embeddings`` with ``summaries`` to include source metadata
    for citation generation.

    Args:
        db: The async database session.
        query: The user's question.
        user_id: Filter results to this user's notes.
        top_k: Maximum number of chunks to return.

    Returns:
        A list of dicts, each containing ``chunk_text``, ``summary_id``,
        ``title``, ``source``, ``source_url``, and ``relevance_score``.
    """
    query_vec = await embed_query(query)
    vec_literal = "[" + ",".join(str(v) for v in query_vec) + "]"

    sql = text("""
        SELECT
            ne.chunk_text,
            ne.summary_id,
            s.title,
            s.source,
            s.source_url,
            1 - (ne.embedding <=> :vec ::vector) AS relevance_score
        FROM note_embeddings ne
        JOIN summaries s ON s.id = ne.summary_id
        WHERE s.user_id = :user_id
          AND ne.embedding IS NOT NULL
        ORDER BY ne.embedding <=> :vec ::vector
        LIMIT :top_k
    """)

    result = await db.execute(
        sql,
        {"vec": vec_literal, "user_id": user_id, "top_k": top_k},
    )
    rows = result.fetchall()

    retrieved = []
    for row in rows:
        retrieved.append({
            "chunk_text": row.chunk_text,
            "summary_id": row.summary_id,
            "title": row.title,
            "source": row.source,
            "source_url": row.source_url,
            "relevance_score": float(row.relevance_score) if row.relevance_score else 0.0,
        })

    logger.info("Retrieved %d chunks for query '%s'", len(retrieved), query[:80])
    return retrieved


RAG_PROMPT = """You are a helpful study assistant answering questions about lecture notes.
Use ONLY the provided sources to answer the question. For every fact you state,
include an inline citation like [SOURCE_1], [SOURCE_2], etc.

If you cannot answer from the provided sources, say "I don't have enough information in your notes to answer this."

SOURCES:
{sources}

QUESTION: {query}

ANSWER (with inline [SOURCE_N] citations):"""


async def generate_answer_with_citations(
    query: str,
    retrieved_chunks: List[Dict[str, Any]],
) -> Tuple[str, List[Dict[str, Any]]]:
    """Generate a RAG answer with inline source citations.

    Constructs a prompt with numbered sources, sends to Gemini 1.5 Flash,
    and parses the ``[SOURCE_N]`` markers in the response.

    Args:
        query: The user's question.
        retrieved_chunks: The list of retrieved chunks from
            :func:`retrieve_with_citations`.

    Returns:
        A tuple of ``(answer_text, citations_list)``.
    """
    if not retrieved_chunks:
        return "I don't have any notes to answer from. Please summarise some content first.", []

    # Build numbered sources
    source_lines: List[str] = []
    for i, chunk in enumerate(retrieved_chunks, start=1):
        source_lines.append(f"[SOURCE_{i}] (from '{chunk['title']}'):\n{chunk['chunk_text'][:1500]}")

    sources_text = "\n\n".join(source_lines)
    prompt = RAG_PROMPT.format(sources=sources_text, query=query)

    model = genai.GenerativeModel("gemini-flash-latest")
    response = model.generate_content(prompt)

    answer = response.text.strip()

    # Build citations metadata
    citations = extract_citations(answer, retrieved_chunks)

    return answer, citations


def extract_citations(
    answer: str,
    retrieved_chunks: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Parse ``[SOURCE_N]`` markers from the answer and map to chunk metadata.

    Args:
        answer: The generated answer text containing ``[SOURCE_N]`` markers.
        retrieved_chunks: The original retrieved chunks (1-indexed mapping).

    Returns:
        A de-duplicated list of citation dicts.
    """
    cited_indices = set()
    for match in re.finditer(r"\[SOURCE_(\d+)\]", answer):
        idx = int(match.group(1)) - 1  # 0-based
        if 0 <= idx < len(retrieved_chunks):
            cited_indices.add(idx)

    citations = []
    for idx in sorted(cited_indices):
        chunk = retrieved_chunks[idx]
        citations.append({
            "source_id": chunk["summary_id"],
            "source_title": chunk["title"],
            "source_type": chunk["source"],
            "chunk_text": chunk["chunk_text"][:500],
            "relevance_score": chunk["relevance_score"],
            "source_url": chunk.get("source_url"),
        })

    return citations


def estimate_time_saved(content_length: int) -> float:
    """Estimate minutes saved by summarising instead of reading/watching.

    Heuristic: average reading speed ~250 words/min.
    A summary takes ~2 minutes to read.

    Args:
        content_length: Number of characters in the raw content.

    Returns:
        Estimated minutes saved (minimum 1.0).
    """
    word_count = content_length / 5  # rough char-to-word ratio
    reading_time = word_count / 250
    summary_reading_time = 2.0
    saved = max(reading_time - summary_reading_time, 1.0)
    return round(saved, 1)
