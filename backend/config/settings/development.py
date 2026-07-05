"""
backend/config/settings/development.py
────────────────────────────────────────
Purpose : Development-only Django settings. Overrides and extends base.py for
          local machine use. Enables DEBUG mode, relaxed CORS, and verbose logging.

          Loads secrets from backend/.env via python-dotenv so you never have to
          export environment variables manually in your terminal.

          IMPORTANT — load_dotenv() MUST run before `from .base import *`.
          base.py reads os.environ["DJANGO_SECRET_KEY"] at import time.
          If dotenv hasn't loaded the .env file yet, that line raises KeyError.
          Order matters: dotenv first, then base.py import.

Used by : manage.py — sets DJANGO_SETTINGS_MODULE=config.settings.development by default
          pytest    — pyproject.toml sets DJANGO_SETTINGS_MODULE to this file for all tests

NOT used by : Dockerfile, Dockerfile.job, Cloud Run, or any GCP service.
              Production always uses config.settings.production.
"""
from pathlib import Path

from dotenv import load_dotenv

# ── Load .env BEFORE importing base.py ───────────────────────────────────────
# base.py reads os.environ["DJANGO_SECRET_KEY"] at module level.
# load_dotenv must populate os.environ first or base.py crashes with KeyError.
# Path: backend/.env (three levels up from this file: settings/ → config/ → backend/)
_BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(_BASE_DIR / ".env")

# ── Now safe to import base.py — all env vars are in os.environ ──────────────
from .base import *  # noqa: F401, F403, E402

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# ── CORS ──────────────────────────────────────────────────────────────────────
# Allow Next.js dev server (localhost:3000) to call the Django API.
# CORS_ALLOW_CREDENTIALS=True lets the browser send Django session/CSRF cookies.
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
]
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
]

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
