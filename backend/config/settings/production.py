"""
backend/config/settings/production.py
───────────────────────────────────────
Purpose : Production-only Django settings used when running on GCP Cloud Run.
          DEBUG is always False. Secrets come from environment variables that
          Cloud Run injects from Secret Manager at container startup — this file
          never reads .env or any file from disk.

          Key differences from development.py:
          - DEBUG=False (never show stack traces to users)
          - Strict security headers (HSTS, secure cookies, SSL redirect)
          - JSON structured logging (Cloud Logging can parse and index these)
          - ALLOWED_HOSTS and CORS_ALLOWED_ORIGINS set from environment variables
            so the same Docker image works for staging and production

Used by : config/wsgi.py       — gunicorn loads this at API server startup
          run_job.py           — ingestion job loads this at startup
          Dockerfile CMD       — sets DJANGO_SETTINGS_MODULE=config.settings.production
          Dockerfile.job CMD   — same

NOT used by : manage.py (uses development), pytest (uses development).
"""
import os

from .base import *  # noqa: F401, F403

DEBUG = False

# Set from environment variable — Terraform outputs the Cloud Run service URL
# which is then set as an env var in the Cloud Run service definition.
# Format: "zeitgeist-api-abc123-uc.a.run.app,yourdomain.com"
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(",")

# Phase 1-2: still "http://localhost:3000" (set via env var in Cloud Run config)
# Phase 3: replaced with the public frontend domain
CORS_ALLOWED_ORIGINS = os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")
CORS_ALLOW_CREDENTIALS = True

# ── Security headers ──────────────────────────────────────────────────────────
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True

# ── Structured JSON logging for Cloud Logging ─────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}
