"""
backend/apps/ingestion/adapters/base.py
─────────────────────────────────────────
Purpose : Defines the BaseSourceAdapter abstract class that ALL source adapters
          must inherit from. Enforces a consistent interface so the orchestrator
          can call any adapter the same way, without knowing its internals.

          Every adapter must implement three methods:

            get_source_name() -> str
              Returns the adapter's identifier string — "hackernews",
              "devto", "nytimes", "rawg", or "football_data". This is stored in
              TrendItem.source and IngestionRun.source_adapter.

            fetch(category: Category) -> list[RawItem]
              Calls the external API for the given category.
              Returns a list of raw, unnormalised items (dicts or dataclasses).
              Should raise an exception on failure so the orchestrator can catch it
              and record the IngestionRun as failed.

            normalise(raw: RawItem, category: Category, rank: int) -> NormalizedTrendItem
              Converts one raw item from the source's format into the common
              schema. Does NOT save to the DB — the orchestrator creates the
              TrendSnapshot first, then bulk saves TrendItem rows.

          Why this pattern?
            Adding a new verified data source means creating a small adapter
            class and registering it in the orchestrator. CategorySourceConfig
            then decides which categories use that adapter.

Used by : Every source adapter inherits from this class:
            hackernews.py, devto.py, nytimes.py, rawg.py, football_data.py
          apps/ingestion/orchestrator.py — calls fetch() and normalise() on each adapter

Phase    : 1 — Week 2
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Generic, TypeVar

from apps.categories.models import Category

RawItem = TypeVar("RawItem")


@dataclass(frozen=True, slots=True)
class NormalizedTrendItem:
    """
    Source-independent trend item data.

    Adapters return this object instead of a TrendItem model because TrendItem
    requires a TrendSnapshot FK. The orchestrator owns snapshot creation.
    """

    title: str
    url: str
    score: int
    score_label: str
    rank: int
    external_url: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)


class BaseSourceAdapter(ABC, Generic[RawItem]):
    """
    Contract every source adapter must follow.

    Concrete adapters own API-specific details. The orchestrator only depends on
    this shared interface, which keeps source-specific branching out of the batch
    coordination code.
    """

    default_limit = 50

    @classmethod
    @abstractmethod
    def get_source_name(cls) -> str:
        """Return the source key stored in CategorySourceConfig and TrendItem."""

    @abstractmethod
    def fetch(self, category: Category, *, limit: int = default_limit) -> list[RawItem]:
        """Fetch raw items from the external source for one category."""

    @abstractmethod
    def normalise(
        self,
        raw_item: RawItem,
        category: Category,
        *,
        rank: int,
    ) -> NormalizedTrendItem:
        """Convert one raw source item into Zeitgeist's common trend shape."""

    def fetch_and_normalise(
        self,
        category: Category,
        *,
        limit: int = default_limit,
    ) -> list[NormalizedTrendItem]:
        """Fetch raw items and return normalized items ranked from 1."""
        raw_items = self.fetch(category, limit=limit)
        return [
            self.normalise(raw_item, category, rank=rank)
            for rank, raw_item in enumerate(raw_items, start=1)
        ]
