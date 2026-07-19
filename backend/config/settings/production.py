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
          - ALLOWED_HOSTS, CORS_ALLOWED_ORIGINS, and CSRF_TRUSTED_ORIGINS set
            from environment variables so the same Docker image works for
            staging and production

Used by : config/wsgi.py       — gunicorn loads this at API server startup
          run_job.py           — ingestion job loads this at startup
          Dockerfile CMD       — sets DJANGO_SETTINGS_MODULE=config.settings.production
          Dockerfile.job CMD   — same

NOT used by : manage.py (uses development), pytest (uses development).
"""
import os

from .base import *  # noqa: F401, F403

DEBUG = False

# Split comma-separated env vars and filter out empty strings.
# os.environ.get("VAR", "").split(",") on an empty string produces [""]
# which Django treats as an invalid host/origin and raises a system check error.
# The filter(None, ...) removes any empty strings from the list.
ALLOWED_HOSTS = list(filter(None, os.environ.get("ALLOWED_HOSTS", "").split(",")))

CORS_ALLOWED_ORIGINS = list(filter(None, os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")))
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = list(filter(None, os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",")))

# ── Security headers ──────────────────────────────────────────────────────────
SECURE_SSL_REDIRECT = True
# Cloud Run terminates HTTPS before forwarding HTTP to the container. Trust its
# forwarded proto header so Django knows the original client request was HTTPS
# and does not redirect an already-secure request during smoke tests.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = "Lax"
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
