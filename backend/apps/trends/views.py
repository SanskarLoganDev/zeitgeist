"""
backend/apps/trends/views.py
──────────────────────────────
Purpose : DRF API views for the dashboard and ingestion admin endpoints.

          Views:
            DashboardView         GET /api/v1/dashboard/
              The main view users see on login. Returns the top 5 TrendItems per
              category for all categories the user has selected in preferences.
              Phase 1: returns all 3 starter categories for all users (no personalisation).
              Phase 2: filtered by UserCategoryPreference, served from Redis cache.

            IngestionRunListView  GET /api/v1/admin/ingestion/runs/
              Staff-only. Returns the full history of IngestionRun records —
              source, status, items_fetched, error_message, timestamps.
              Displayed in the Django admin panel and accessible via the API
              for future monitoring integrations.

            IngestionTriggerView  POST /api/v1/admin/ingestion/trigger/
              Staff-only. Manually triggers an ingestion run for a specific source.
              Used during development and when a run fails and needs a re-fetch (FR-19).

Used by : apps/trends/urls.py    — routes requests to these views
          Next.js frontend       — DashboardView is the first page after login
          Django admin           — IngestionRunListView powers the log display

Phase    : 1 Week 3 — DashboardView (basic, no cache, all categories)
           Phase 2   — DashboardView with Redis cache + preference filtering
           Phase 1 Week 2 — IngestionRunListView, IngestionTriggerView
"""
# Implementation coming in Phase 1 Week 2 (admin views) and Week 3 (dashboard)
