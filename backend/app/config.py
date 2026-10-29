"""
Application configuration loaded from environment variables.

Uses pydantic-settings for typed, validated configuration with sensible defaults.
All secrets are read from the environment (or a .env file during development).
"""

from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralised application settings.

    Every attribute maps to an environment variable of the same name
    (case-insensitive). A ``.env`` file in the project root is loaded
    automatically when present.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Database ──────────────────────────────
    database_url: str = "postgresql+asyncpg://studypilot:studypilot@postgres:5432/studypilot"
    database_url_sync: str = "postgresql://studypilot:studypilot@postgres:5432/studypilot"

    # ── Redis / Celery ────────────────────────
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/1"

    # ── Auth / JWT ────────────────────────────
    secret_key: str = "change-me-to-a-random-64-char-string"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours

    # ── Gemini API ────────────────────────────
    gemini_api_key: str = ""

    # ── OpenAI (Whisper fallback) ─────────────
    openai_api_key: str = ""

    # ── CORS ──────────────────────────────────
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    # ── Rate limiting ─────────────────────────
    rate_limit_per_minute: int = 10

    # ── W&B ───────────────────────────────────
    wandb_api_key: str = ""
    wandb_project: str = "studypilot"

    # ── Email (optional) ─────────────────────
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""

    @property
    def cors_origin_list(self) -> List[str]:
        """Parse comma-separated CORS origins into a list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache()
def get_settings() -> Settings:
    """Return a cached :class:`Settings` singleton.

    Using ``lru_cache`` ensures the ``.env`` file and environment are
    only read once per process lifetime.
    """
    return Settings()
