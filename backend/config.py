"""Environment-driven application configuration.

All secrets come from the environment (or a .env file in backend/).
Never hardcode credentials in source.
"""
import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()


class Config:
    # Local dev default points at the platform's dedicated role/database.
    # Override with DATABASE_URL (e.g. docker-compose, staging, prod).
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://health:health@localhost:5432/health_platform",
    )
    JWT_SECRET_KEY = os.getenv(
        "JWT_SECRET_KEY",
        "dev-only-insecure-secret-change-me-0123456789abcdef0123456789abcdef",
    )
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)

    # The SPA authenticates with the HttpOnly session cookie; header auth stays
    # enabled for server-to-server clients and tests.
    JWT_TOKEN_LOCATION = ["headers", "cookies"]
    JWT_COOKIE_SECURE = os.getenv("JWT_COOKIE_SECURE", "0") == "1"
    JWT_COOKIE_SAMESITE = "Lax"
    JWT_COOKIE_CSRF_PROTECT = True

    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

    # Shared storage keeps rate limits consistent across workers/replicas.
    # Set to a sqlalchemy:// or redis:// URL in production (memory:// in dev).
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")

    # The login response carries a Bearer token for environments that drop
    # cookies. In production set to "0": only the HttpOnly cookie is issued.
    AUTH_ISSUE_FALLBACK_TOKEN = os.getenv("AUTH_ISSUE_FALLBACK_TOKEN", "1") == "1"

    # LLM chat: any OpenAI-compatible endpoint. Default is local inference via
    # Ollama (no API key); a hosted provider works by setting LLM_API_KEY and
    # LLM_BASE_URL. When the endpoint is unreachable the assistant falls back
    # to a deterministic rule-based coach, so the platform works offline.
    LLM_API_KEY = os.getenv("LLM_API_KEY", "")
    LLM_MODEL = os.getenv("LLM_MODEL", "mistral-3b")
    LLM_BASE_URL = os.getenv(
        "LLM_BASE_URL", "http://localhost:11434/v1/chat/completions"
    )

    JSON_AS_ASCII = False
    # Local models can be slow on CPU: configurable per-request timeout.
    LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "90"))
