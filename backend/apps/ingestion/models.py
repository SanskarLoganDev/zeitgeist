"""
backend/apps/ingestion/models.py
──────────────────────────────────
Purpose : Defines the IngestionRun model — the audit log for every ingestion attempt.

          IngestionRun
            One record is written per source adapter per daily run.
            If there are 3 categories × 2 sources (Reddit + HN), that's 6 records
            written after each run.

            Fields:
              source_adapter  : which adapter ran — "reddit", "hackernews", etc.
              category        : which category this run served
              status          : "success" | "partial" | "failed"
              items_fetched   : how many TrendItems were written
              error_message   : null on success, exception message on failure
              started_at      : when the adapter began fetching
              completed_at    : when it finished (or failed)

            This powers:
              - Django admin ingestion log (FR-19)
              - The stale data indicator on category pages (FR-13) — the frontend
                reads last_updated from the most recent successful IngestionRun
                for that category
              - Phase 3: Cloud Monitoring alert if no successful run in 25+ hours

Used by : apps/ingestion/orchestrator.py — creates and updates IngestionRun records
          apps/trends/views.py           — reads latest run timestamp for stale indicator
          apps/trends/admin.py           — displays run history in Django admin
          apps/trends/views.py (admin)   — IngestionRunListView returns run history via API

Phase    : 1 — Week 2
"""
# Implementation coming in Phase 1 Week 2
