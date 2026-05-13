"""
backend/apps/ingestion/adapters/hackernews.py
──────────────────────────────────────────────
Purpose : Fetches top stories from Hacker News using the official Firebase API.
          The HN API is completely free, requires no authentication, and has no
          documented rate limit — making it the most reliable source in the pipeline.

          Endpoint used:
            https://hacker-news.firebaseio.com/v0/topstories.json  → list of top story IDs
            https://hacker-news.firebaseio.com/v0/item/{id}.json   → story detail

          Normalised fields:
            title        → story title
            url          → the URL the story links to (external article/repo)
            source       → "hackernews"
            score        → HN points
            score_label  → "points"

          Used for: Tech and Research categories primarily.
          HN aggregates the highest-quality tech/research links from the community —
          a strong signal that complements Reddit's broader discussion volume.

Used by : apps/ingestion/orchestrator.py — instantiated for categories where
            CategorySourceConfig has source="hackernews"

Phase    : 1 — Week 2
"""
# Implementation coming in Phase 1 Week 2
