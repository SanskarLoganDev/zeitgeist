"""
backend/apps/ingestion/adapters/base.py
─────────────────────────────────────────
Purpose : Defines the BaseSourceAdapter abstract class that ALL source adapters
          must inherit from. Enforces a consistent interface so the orchestrator
          can call any adapter the same way, without knowing its internals.

          Every adapter must implement three methods:

            get_source_name() -> str
              Returns the adapter's identifier string — "reddit", "hackernews",
              "youtube" etc. This is stored in TrendItem.source and IngestionRun.source_adapter.

            fetch(category: Category) -> list[RawItem]
              Calls the external API for the given category.
              Returns a list of raw, unnormalised items (dicts or dataclasses).
              Should raise an exception on failure so the orchestrator can catch it
              and record the IngestionRun as failed.

            normalise(raw: RawItem, category: Category) -> TrendItem (unsaved)
              Converts one raw item from the source's format into a TrendItem
              using the common schema. Does NOT save to the DB — the orchestrator
              handles bulk saving after all items are normalised.

          Why this pattern?
            Adding a new data source (e.g. Spotify) means only creating a new
            class that inherits from BaseSourceAdapter. The orchestrator picks it
            up automatically from the CategorySourceConfig DB table. No changes
            to the orchestrator or any other file needed.

Used by : Every source adapter inherits from this class:
            reddit.py, hackernews.py, youtube.py, arxiv.py,
            pubmed.py, tmdb.py, steam.py, nasa.py, google_trends.py
          apps/ingestion/orchestrator.py — calls fetch() and normalise() on each adapter

Phase    : 1 — Week 2
"""
# Implementation coming in Phase 1 Week 2
