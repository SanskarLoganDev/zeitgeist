"""
backend/apps/categories/views.py
─────────────────────────────────
Purpose : DRF API views for category listing and user preference management.

          Views:
            CategoryListView      GET /api/v1/categories/
              Returns all active categories with metadata (name, slug, source count,
              last_updated timestamp from the most recent IngestionRun).
              Used by Next.js to render the sidebar category list.

            CategoryDetailView    GET /api/v1/categories/{slug}/
              Returns top trending items for a category plus the Gemini AI summary
              (Phase 2). Checks Redis cache first; falls back to Postgres on miss.

            CategoryTrendsView    GET /api/v1/categories/{slug}/trends/
              Returns trend chart data — relative interest over a time window.
              Uses stored snapshots for recent windows, pytrends for historical.
              Phase 2 feature.

            CategoryItemsView     GET /api/v1/categories/{slug}/items/
              Paginated, filterable list of TrendItems. Supports ?source= and
              ?window= query params for source filter (FR-09) and time window (FR-07).
              Phase 2 feature.

            PreferencesView       PATCH /api/v1/categories/preferences/
              Updates the authenticated user's selected categories.
              Called by the inline preference editor on the dashboard (FR-03).

Used by : apps/categories/urls.py — routes requests to these views
          Next.js frontend        — dashboard, category pages, preference sidebar

Phase    : 1 Week 3 — CategoryListView
           Phase 2   — all other views
"""
# Implementation coming in Phase 1 Week 3 (CategoryListView)
# Remaining views in Phase 2
