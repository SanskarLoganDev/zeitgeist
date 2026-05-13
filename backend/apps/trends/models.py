"""
backend/apps/trends/models.py
───────────────────────────────
Purpose : Defines the core data models for trend storage and retrieval.

          Models:
            TrendSnapshot
              - One record per (category, ingestion run).
              - The anchor for a daily set of trend data.
              - Example: { category: Gaming, run: run_2026_05_13, created_at: ... }
              - This is what makes historical 7/30/90-day views possible (FR-07).
                Data accumulates from the very first ingestion run (FR-12).

            TrendItem
              - One record per trending post/paper/video/game within a snapshot.
              - source field identifies which adapter produced it:
                reddit | hackernews | youtube | arxiv | pubmed | tmdb | steam | nasa
              - score and score_label are normalised — upvotes for Reddit, points
                for HN, views for YouTube, citations for arXiv etc.
              - ai_summary (Phase 2): one-line Gemini-generated summary per item
              - sentiment (Phase 3): Positive / Negative / Neutral badge

            CategoryAISummary (Phase 2)
              - One record per (category, ingestion run).
              - Stores the Gemini-generated 2–4 sentence trend summary.
              - Displayed at the top of each category page.

            CrossPlatformTopic (Phase 3)
              - Written by the embedding cross-platform detection job.
              - Surfaced as "trending everywhere" badges (FR-10).

Used by : apps/trends/views.py       — dashboard and category detail reads
          apps/ingestion/orchestrator.py — writes TrendSnapshot + TrendItem records
          apps/ai/client.py          — reads TrendItems to feed to Gemini
          Django admin               — staff can inspect ingestion output
          Next.js frontend           — indirectly via the REST API responses

Phase    : 1 — Week 2 (TrendSnapshot, TrendItem)
           Phase 2 — CategoryAISummary
           Phase 3 — CrossPlatformTopic
"""
# Implementation coming in Phase 1 Week 2
