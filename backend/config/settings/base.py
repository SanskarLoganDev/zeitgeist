"""
backend/config/settings/base.py
────────────────────────────────
Purpose : Shared Django settings used in ALL environments (development and production).
          Contains everything that never changes between environments:
          installed apps, middleware stack, DRF config, database schema,
          auth validators, i18n, and static file config.

          Secrets (SECRET_KEY, DB_PASSWORD etc.) are read from environment variables
          here — they are never hardcoded. On GCP, these env vars are injected from
          Secret Manager at Cloud Run startup. Locally, they are loaded from
          backend/.env by development.py via python-dotenv.

Used by : config/settings/development.py  — imports everything via `from .base import *`
          config/settings/production.py   — imports everything via `from .base import *`
          config/wsgi.py                  — loaded at production API server startup
          run_job.py                      — loaded by ingestion job at startup
          manage.py                       — defaults to development settings
          All Django apps                 — Django reads this at startup for every request

NOT used by : Frontend (Next.js), Terraform, or GitHub Actions directly.
              Those interact with the running Django server, not its settings file.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ── Security ──────────────────────────────────────────────────────────────────
# Read from environment — set in .env locally, Secret Manager on GCP.
# Using os.environ["KEY"] (not .get) intentionally — if the key is missing,
# Django will crash immediately at startup with a clear error rather than
# silently running with no secret key.
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
ALLOWED_HOSTS: list[str] = []

# ── Application definition ────────────────────────────────────────────────────
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",   # Django REST Framework — powers all /api/v1/ endpoints
    "corsheaders",      # Handles CORS headers so Next.js on localhost can call Django
]

LOCAL_APPS = [
    "apps.accounts",    # User model, Google OAuth, JWT
    "apps.categories",  # Category, CategorySourceConfig
    "apps.trends",      # TrendSnapshot, TrendItem, CategoryAISummary, dashboard API
    "apps.ingestion",   # IngestionRun model, orchestrator, source adapters
    "apps.ai",          # Vertex AI client wrappers, Gemini prompts, embeddings
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    # CorsMiddleware MUST be first — adds headers before any response goes out
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ── Database ──────────────────────────────────────────────────────────────────
# All values come from environment variables.
# Locally  : set in backend/.env, loaded by development.py via python-dotenv
# On GCP   : DB_PASSWORD injected from Secret Manager
#            DB_HOST is the Cloud SQL Unix socket path:
#            /cloudsql/project:region:instance — NOT a TCP host
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "zeitgeist"),
        "USER": os.environ.get("DB_USER", "zeitgeist"),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", "5432"),
    }
}

# ── Custom user model ─────────────────────────────────────────────────────────
# Tells Django to use apps.accounts.User instead of the built-in User model.
# CRITICAL: this must be set before the FIRST migration is ever created.
# Changing it after migrations exist requires wiping the database.
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ── Django REST Framework ─────────────────────────────────────────────────────
#
# WEEK 1 — authentication is intentionally open so the health check works
# and CI passes. There are no protected endpoints yet anyway.
#
# WEEK 3 — swap in the real auth class once JWTCookieAuthentication exists:
#   "DEFAULT_AUTHENTICATION_CLASSES": [
#       "apps.accounts.authentication.JWTCookieAuthentication",
#   ],
#   "DEFAULT_PERMISSION_CLASSES": [
#       "rest_framework.permissions.IsAuthenticated",
#   ],
#
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    # AllowAny means any request reaches the view without an auth check.
    # Safe for now — the only live endpoint is /api/v1/health/ which has
    # no sensitive data. Locked down in Week 3 when user-specific views exist.
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}

# ── Internationalisation ──────────────────────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True  # All datetimes stored as UTC in the DB — never localised at rest

# ── Static files ──────────────────────────────────────────────────────────────
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"  # collectstatic target for Django admin CSS

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── Email / SMTP ──────────────────────────────────────────────────────────────
# Used for account verification OTPs. Locally these values come from .env.
# In production they should be injected as Cloud Run environment variables or
# Secret Manager references owned by CD, not committed to source control.
EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND",
    "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "true").lower() == "true"
EMAIL_USE_SSL = os.environ.get("EMAIL_USE_SSL", "false").lower() == "true"
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER)

EMAIL_VERIFICATION_OTP_TTL_MINUTES = int(
    os.environ.get("EMAIL_VERIFICATION_OTP_TTL_MINUTES", "10")
)
EMAIL_VERIFICATION_MAX_ATTEMPTS = int(
    os.environ.get("EMAIL_VERIFICATION_MAX_ATTEMPTS", "5")
)
EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS = int(
    os.environ.get("EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS", "60")
)

# ── AI summaries ──────────────────────────────────────────────────────────────
# The ingestion job uses these to generate stored category summaries through
# Vertex AI / Gemini. User-facing API requests never call Gemini directly.
AI_SUMMARIES_ENABLED = os.environ.get("AI_SUMMARIES_ENABLED", "false").lower() == "true"
GOOGLE_CLOUD_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
GOOGLE_CLOUD_LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")
