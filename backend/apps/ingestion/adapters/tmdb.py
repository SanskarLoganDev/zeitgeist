"""
backend/apps/ingestion/adapters/tmdb.py
─────────────────────────────────────────
Purpose : Fetches trending movies and TV shows from The Movie Database (TMDB) API.
          Used for the TV/Movies category to provide structured entertainment data
          that complements broader movie/TV discussion.

          API used: /trending/movie/day and /trending/tv/day endpoints.
          Free API key required — no rate limit issues at our volume (40 req/10sec).
          Credential: TMDB_API_KEY from Secret Manager.

          Normalised fields:
            title        → movie or show title
            url          → https://www.themoviedb.org/movie/{id} or /tv/{id}
            source       → "tmdb"
            score        → TMDB popularity score (rolling window metric)
            score_label  → "popularity"

Used by : apps/ingestion/orchestrator.py — instantiated for categories where
            CategorySourceConfig has source="tmdb"

Phase    : 2 — Week 5
"""
# Implementation coming in Phase 2 Week 5
