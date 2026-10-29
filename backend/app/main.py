"""
StudyPilot – FastAPI application entry point.

This module assembles all routers, middleware, CORS, and lifecycle hooks
into a single FastAPI application instance.
"""

from __future__ import annotations

import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db
from app.middleware import RateLimitMiddleware, RequestLoggingMiddleware
from app.routes.analytics import router as analytics_router
from app.routes.ask import router as ask_router
from app.routes.auth import router as auth_router
from app.routes.search import router as search_router
from app.routes.summarise import router as summarise_router
from app.routes.tasks import router as tasks_router
from app.routes.websocket import router as ws_router
from app.schemas import HealthResponse

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

settings = get_settings()

from contextlib import asynccontextmanager

# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for the FastAPI application."""
    logger.info("Starting StudyPilot API v1.0.0")
    
    try:
        await init_db()
        logger.info("Database initialised successfully")
    except Exception as exc:
        logger.error("Database initialisation failed: %s", exc)
    
    yield
    
    logger.info("Shutting down StudyPilot API")

# ── Application ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="StudyPilot API",
    description=(
        "AI-powered study co-pilot that converts YouTube lectures and PDFs "
        "into structured notes, answers questions with citations, and "
        "provides semantic search across your knowledge base."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Custom middleware ─────────────────────────────────────────────────────────
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RateLimitMiddleware)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(summarise_router)
app.include_router(ask_router)
app.include_router(search_router)
app.include_router(analytics_router)
app.include_router(tasks_router)
app.include_router(ws_router)


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health_check():
    """Health check endpoint for load balancers and container orchestration.

    Returns:
        ``{"status": "ok", "version": "1.0.0"}``
    """
    return HealthResponse(status="ok", version="1.0.0")
