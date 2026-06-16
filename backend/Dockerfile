# ── API server Dockerfile ─────────────────────────────────────────────────────
# Multi-stage build. Final image is minimal — no dev dependencies.
# Used by Cloud Run (zeitgeist-api) via GitHub Actions CD pipeline.
#
# Port: 8000 (gunicorn binds here — tell Cloud Run via --port 8000 in cd.yml)
# Entrypoint: gunicorn config.wsgi:application

FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps for psycopg2-binary
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

# ── Dependencies stage ────────────────────────────────────────────────────────
FROM base AS deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM base AS runtime
COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin
COPY . .

# Collect static files using a dummy secret key — real key only needed at runtime.
# collectstatic doesn't need DB access or real credentials, just Django to load.
# DJANGO_SECRET_KEY is not available at build time (injected by Cloud Run at startup).
RUN DJANGO_SECRET_KEY=build-time-dummy-key-not-used-in-production \
    python manage.py collectstatic --noinput \
    --settings=config.settings.production || true

EXPOSE 8000

# Gunicorn: 2 workers for I/O-bound Django on Cloud Run
# Binds to port 8000 — must match --port 8000 in cd.yml deploy step
CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "2", \
     "--timeout", "30", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
