"""
backend/config/settings/development.py
────────────────────────────────────────
Purpose : Development-only Django settings. Overrides and extends base.py for
          local machine use. Enables DEBUG mode, relaxed CORS, and verbose logging.

          Loads secrets from backend/.env via python-dotenv so you never have to
          export environment variables manually in your terminal.

Used by : manage.py — sets DJANGO_SETTINGS_MODULE=config.settings.development by default
          pytest    — pyproject.toml sets DJANGO_SETTINGS_MODULE to this file for all tests
          docker-compose — not directly, but the Django process running on the host uses this

NOT used by : Dockerfile, Dockerfile.job, Cloud Run, or any GCP service.
              Production always uses config.settings.production.
"""
from .base import *  # noqa: F401, F403 — intentional wildcard import for settings layering
import os
from dotenv import load_dotenv

# Load backend/.env into the process environment before base.py reads os.environ
load_dotenv(BASE_DIR / ".env")  # noqa: F405 — BASE_DIR imported from base.py via *

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# ── CORS ──────────────────────────────────────────────────────────────────────
# Allow Next.js dev server (localhost:3000) to call the Django API.
# CORS_ALLOW_CREDENTIALS=True is required so the browser sends the JWT cookie.
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
]
CORS_ALLOW_CREDENTIALS = True

# ── Logging ───────────────────────────────────────────────────────────────────
# Plain text to console — readable in your terminal.
# Production uses JSON format so Cloud Logging can parse structured fields.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "root": {
        "handlers": ["console"],
        "level": "DEBUG",
    },
}
