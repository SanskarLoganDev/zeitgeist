# ── API server Dockerfile ─────────────────────────────────────────────────────
# Multi-stage build. Final image is minimal — no dev dependencies.
# Used by Cloud Run (trendpulse-api) and by docker-compose locally.

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

# Collect static files (admin CSS etc.)
RUN python manage.py collectstatic --noinput \
    --settings=config.settings.production || true

EXPOSE 8000

# Gunicorn: 2 workers * (2 * CPU + 1) — good for I/O-bound Django on Cloud Run
CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "2", \
     "--timeout", "30", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
