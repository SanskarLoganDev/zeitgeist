"""
backend/apps/ingestion/adapters/youtube.py
────────────────────────────────────────────
Purpose : Fetches trending videos from the YouTube Data API v3.
          Used for Gaming, TV/Movies, and Food categories where video content
          provides a richer signal than text discussion alone.

          API used: videos.list with chart=mostPopular, filtered by videoCategoryId.
          Quota: 10,000 units/day on the free tier. Each list call costs ~1 unit.

          Normalised fields:
            title        → video title
            url          → https://youtube.com/watch?v={videoId}
            source       → "youtube"
            score        → view count
            score_label  → "views"

          Credential: YOUTUBE_API_KEY from Secret Manager.

Used by : apps/ingestion/orchestrator.py — instantiated for categories where
            CategorySourceConfig has source="youtube"

Phase    : 2 — Week 5
"""
# Implementation coming in Phase 2 Week 5
