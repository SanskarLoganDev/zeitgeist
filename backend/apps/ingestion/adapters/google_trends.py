"""
backend/apps/ingestion/adapters/google_trends.py
──────────────────────────────────────────────────
Purpose : Fetches historical interest data from Google Trends using pytrends.
          Unlike all other adapters, this one does NOT produce TrendItems —
          it produces time-series data for the trend charts (FR-08).

          Used for: the long-term historical curve on category pages.
          Example: "interest in 'Rust programming' from 2020 to today"
          gives the user context on whether something is genuinely new or
          just cyclically resurging.

          IMPORTANT: pytrends is an UNOFFICIAL library that scrapes Google Trends.
          Google has no public API for this data. pytrends works by mimicking
          browser requests. It is stable but can occasionally break after
          Google UI changes. Treat its output as best-effort, not guaranteed.

          Rate limiting: requests must be batched carefully with delays to avoid
          Google blocking the IP. Never call this in a tight loop.

          Used for: Phase 2 Week 6 — trend chart data endpoint
            GET /api/v1/categories/{slug}/trends/?window=90d

Used by : apps/categories/views.py (CategoryTrendsView) — on cache miss for historical data
          NOT called by the orchestrator — this is called on-demand from the API,
          not during the nightly ingestion job (pytrends has higher latency).

Phase    : 2 — Week 6
"""
# Implementation coming in Phase 2 Week 6
