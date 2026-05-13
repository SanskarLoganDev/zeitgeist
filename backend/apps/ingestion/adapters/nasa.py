"""
backend/apps/ingestion/adapters/nasa.py
─────────────────────────────────────────
Purpose : Fetches featured content from NASA Open APIs.
          Used for the Space category to enrich Reddit/arXiv discussion with
          official NASA mission data and astronomy content.

          APIs used:
            APOD (Astronomy Picture of the Day): daily featured image with explanation
            NeoWs (Near Earth Objects): asteroids and close approach data
            Mars Rover Photos: latest images from Curiosity/Perseverance

          Free API key required — 1,000 requests/hour limit (we use ~3/day).
          Credential: NASA_API_KEY from Secret Manager.

          Normalised fields:
            title        → content title or object name
            url          → NASA page or image URL
            source       → "nasa"
            score        → recency rank (NASA doesn't have engagement metrics)
            score_label  → "featured"

Used by : apps/ingestion/orchestrator.py — instantiated for categories where
            CategorySourceConfig has source="nasa"

Phase    : 2 — Week 5
"""
# Implementation coming in Phase 2 Week 5
