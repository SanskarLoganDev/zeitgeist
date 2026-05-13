"""
backend/apps/ingestion/admin.py
─────────────────────────────────
Purpose : Registers the IngestionRun model in Django admin.
          This is the primary operational dashboard for monitoring the
          health of the daily ingestion pipeline (FR-19).

          What admins see and can do:
            - View all ingestion run records: source, category, status,
              items fetched, error message, start/end timestamps
            - Filter by status (success/failed) and date
            - Search by source adapter name
            - Manually trigger a re-fetch by calling the IngestionTriggerView
              (linked from admin or via the API)

Used by : Django admin panel — loaded automatically at startup
          Staff users — check this after every nightly run to confirm health

Phase    : 1 — Week 2
"""
from django.contrib import admin

# Phase 1 Week 2:
# from .models import IngestionRun
# admin.site.register(IngestionRun)
