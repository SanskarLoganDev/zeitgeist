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
          config/settings/wsgi.py         — loaded at production startup
          config/settings/run_job.py      — loaded by ingestion job at startup
          manage.py                       — sets DJANGO_SETTINGS_MODULE to development
          All Django apps                 — Django reads this at startup for every request

NOT used by : Frontend (Next.js), Terraform, or GitHub Actions directly.
              Those interact with the running Django server, not its settings file.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ── Security ──────────────────────────────────────────────────────────────────
# Read from environment — set in .env locally, Secret Manager on GCP
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
    "rest_framework",       # Django REST Framework — powers all /api/v1/ endpoints
    "corsheaders",          # Handles CORS headers so Next.js on localhost can call Django
]

LOCAL_APPS = [
    "apps.accounts",        # User model, Google OAuth, JWT
    "apps.categories",      # Category, SubredditConfig, CategorySourceConfig
    "apps.trends",          # TrendSnapshot, TrendItem, CategoryAISummary, dashboard API
    "apps.ingestion",       # IngestionRun model, orchestrator, source adapters
    "apps.ai",              # Vertex AI client wrappers, Gemini prompts, embeddings
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    # CorsMiddleware MUST be first — it needs to add headers before any response goes out
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
# Locally: set in backend/.env
# On GCP:  DB_PASSWORD comes from Secret Manager; DB_HOST is the Cloud SQL socket path
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
# Must be set before the first migration — cannot be changed after.
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ── Django REST Framework ─────────────────────────────────────────────────────
# All API views use JWT cookie auth by default.
# JWTCookieAuthentication is implemented in apps/accounts/authentication.py (Phase 1 Week 3)
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.accounts.authentication.JWTCookieAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}

# ── Internationalisation ──────────────────────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True  # All datetimes stored as UTC in the DB

# ── Static files ──────────────────────────────────────────────────────────────
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"  # Where collectstatic puts files for the admin panel

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
