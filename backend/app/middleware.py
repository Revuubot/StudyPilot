"""
FastAPI middleware for request logging, rate limiting, and timing.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ── In-memory rate-limit store (per-process; use Redis for multi-worker) ─────
_rate_store: dict[str, list[float]] = defaultdict(list)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every request with method, path, status, and latency.

    Also writes to the ``api_logs`` table when a database session is
    available on the request state.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Process the request, measure timing, and log results."""
        request_id = str(uuid.uuid4())[:8]
        start = time.perf_counter()

        # Attach request_id for downstream use
        request.state.request_id = request_id
        request.state.start_time = start

        response: Response = await call_next(request)

        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "[%s] %s %s → %d (%.1f ms)",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.1f}"
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple sliding-window rate limiter.

    Limits each IP address to ``RATE_LIMIT_PER_MINUTE`` requests per
    60-second window.  Returns HTTP 429 when exceeded.

    For production multi-worker deployments, replace the in-memory store
    with a Redis-backed counter.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Check rate limit before forwarding the request."""
        # Skip rate limiting for health checks and docs
        if request.url.path in ("/health", "/docs", "/openapi.json", "/redoc"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window = 60.0  # seconds

        # Clean old entries
        _rate_store[client_ip] = [
            ts for ts in _rate_store[client_ip] if now - ts < window
        ]

        if len(_rate_store[client_ip]) >= settings.rate_limit_per_minute:
            logger.warning("Rate limit exceeded for %s", client_ip)
            return Response(
                content='{"detail":"Rate limit exceeded. Try again in a minute."}',
                status_code=429,
                media_type="application/json",
            )

        _rate_store[client_ip].append(now)
        return await call_next(request)
