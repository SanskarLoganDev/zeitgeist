"""
backend/apps/ingestion/adapters/steam.py
──────────────────────────────────────────
Purpose : Fetches top-played and trending games from Steam Spy and IGDB.
          Used for the Gaming category to provide concrete player count data —
          not just Reddit discussion, but actual numbers of people playing.

          Sources:
            Steam Spy API (free): top games by concurrent players, owner estimates
            IGDB API (free via Twitch OAuth): trending games, upcoming releases

          Normalised fields:
            title        → game name
            url          → https://store.steampowered.com/app/{appid}/
            source       → "steam"
            score        → concurrent player count (from Steam Spy)
            score_label  → "players"

          Credential: IGDB requires a Twitch client ID and secret (free).

Used by : apps/ingestion/orchestrator.py — instantiated for categories where
            CategorySourceConfig has source="steam"

Phase    : 2 — Week 5
"""
# Implementation coming in Phase 2 Week 5
