"""
backend/apps/ingestion/adapters/arxiv.py
──────────────────────────────────────────
Purpose : Fetches recently submitted papers from arXiv using their free REST API.
          Used for Research, AI, and Space categories to surface academic signal
          that complements Reddit discussion — a paper trending on arXiv AND on
          Reddit is a much stronger signal than either alone.

          API used: http://export.arxiv.org/api/query with search_query and sortBy=submittedDate
          No authentication required. Polite crawling expected (small delays between requests).

          Normalised fields:
            title        → paper title
            url          → https://arxiv.org/abs/{arxiv_id}
            source       → "arxiv"
            score        → submission recency rank (arXiv has no upvote/citation count in API)
            score_label  → "recent submissions"

Used by : apps/ingestion/orchestrator.py — instantiated for categories where
            CategorySourceConfig has source="arxiv"

Phase    : 2 — Week 5
"""
# Implementation coming in Phase 2 Week 5
