"""
backend/apps/ingestion/adapters/steam.py
──────────────────────────────────────────
Purpose : DEFERRED SOURCE. Fetches top-played and trending games from Steam Spy and IGDB.
          Used for the Gaming category to provide concrete player count data —
          not just social discussion, but actual numbers of people playing.

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

Phase    : Deferred — Steam Spy/IGDB is higher-risk than the other public APIs
           because IGDB needs Twitch OAuth and Steam Spy is less official.
"""
# Implementation intentionally deferred.
