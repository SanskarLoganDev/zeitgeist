"""
backend/run_job.py
──────────────────
Purpose : Entrypoint for the Cloud Run Job (the daily ingestion + AI processing batch).
          Cloud Scheduler fires an HTTP POST at 03:00 UTC → Cloud Run Job starts a
          container using this file as its CMD.

          Sequence:
            1. Sets DJANGO_SETTINGS_MODULE to production
            2. Calls django.setup() so all models and ORM are available
            3. Calls apps.ingestion.orchestrator.run() which:
               - Fetches trending data from all configured source adapters
               - Writes TrendSnapshot + TrendItem records to Postgres
               - Records IngestionRun log entries
               - Phase 2+: calls Gemini for AI summaries and sentiment tags
               - Phase 3+: runs cross-platform topic detection via embeddings

Used by : Cloud Run Job (Dockerfile.job sets CMD ["python", "run_job.py"])
          Cloud Scheduler → triggers the Cloud Run Job → container runs this file

NOT used by : The API server (Dockerfile/wsgi.py), manage.py, or the frontend.
              This file runs once per day and exits. It is not a web server.
"""
import os
import sys
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")
django.setup()

from apps.ingestion.orchestrator import run  # noqa: E402 — must come after django.setup()


if __name__ == "__main__":
    sys.exit(run())
