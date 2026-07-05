"""
backend/apps/ingestion/orchestrator.py
────────────────────────────────────────
Purpose : The main coordinator for the daily ingestion batch job.
          This is what run_job.py calls. It runs every adapter for every
          active category, handles failures gracefully, and triggers AI
          processing after data collection is complete.

          Execution sequence:
            1. Load all active categories from DB (with their source adapter configs)
            2. For each category:
               a. For each configured source adapter:
                  - Create an IngestionRun record (status=running)
                  - Call adapter.fetch() to get raw items from the source API
                  - Call adapter.normalise() on each raw item → TrendItem
                  - Write TrendSnapshot + TrendItems to Postgres
                  - Update IngestionRun (status=success, items_fetched=N)
                  - On exception: update IngestionRun (status=failed, error_message=...)
                    log the error, and CONTINUE to the next adapter (FR-13)
            3. Phase 2+: for each category, call ai/client.py → Gemini summary
            4. Phase 3:  run cross-platform topic detection via embeddings
            5. Invalidate Redis cache for all affected categories (Phase 2)

          Key design principle (FR-13):
            Each adapter is isolated in a try/except. One failing source
            (e.g. one API rate-limits) never stops other sources from running.
            The last successful snapshot is always served to users.

Used by : run_job.py — calls orchestrator.run() as the job entrypoint
          apps/trends/views.py (IngestionTriggerView) — admin manual re-trigger

Phase    : 1 — Week 2 (HN adapter only)
           Phase 2 — all 9 sources + Gemini AI processing
           Phase 3 — cross-platform detection + Redis cache invalidation
"""
from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any, TypeAlias

from django.db import transaction
from django.utils import timezone

from apps.categories.models import Category
from apps.ingestion.adapters.base import BaseSourceAdapter, NormalizedTrendItem
from apps.ingestion.adapters.devto import DevToAdapter
from apps.ingestion.adapters.hackernews import HackerNewsAdapter
from apps.ingestion.models import IngestionRun
from apps.trends.models import TrendItem, TrendSnapshot

logger = logging.getLogger(__name__)

SourceAdapter: TypeAlias = BaseSourceAdapter[Any]  # noqa: UP040
AdapterRegistry: TypeAlias = Mapping[str, type[SourceAdapter]]  # noqa: UP040

ADAPTER_REGISTRY: AdapterRegistry = {
    DevToAdapter.get_source_name(): DevToAdapter,
    HackerNewsAdapter.get_source_name(): HackerNewsAdapter,
}

DEFAULT_ITEM_LIMIT = 20


def run() -> int:
    """
    Main entrypoint called by run_job.py.
    Returns 0 on success, 1 if any adapter failed (for Cloud Run Job exit code).
    """
    return run_with_adapters(ADAPTER_REGISTRY)


def run_with_adapters(
    adapter_registry: AdapterRegistry,
    *,
    item_limit: int = DEFAULT_ITEM_LIMIT,
) -> int:
    """Run ingestion for every active category/source config."""
    had_failure = False
    categories = Category.objects.filter(is_active=True).prefetch_related("source_configs")

    for category in categories:
        source_configs = category.source_configs.filter(is_active=True)
        for source_config in source_configs:
            adapter_class = adapter_registry.get(source_config.source)
            if adapter_class is None:
                _record_unknown_source(category, source_config.source)
                had_failure = True
                continue

            adapter = adapter_class()
            success = _run_source_adapter(
                adapter,
                category=category,
                source=source_config.source,
                item_limit=item_limit,
            )
            if not success:
                had_failure = True

    return 1 if had_failure else 0


def _run_source_adapter(
    adapter: SourceAdapter,
    *,
    category: Category,
    source: str,
    item_limit: int,
) -> bool:
    ingestion_run = IngestionRun.objects.create(
        category=category,
        source_adapter=source,
        status=IngestionRun.STATUS_RUNNING,
    )

    try:
        normalized_items = adapter.fetch_and_normalise(category, limit=item_limit)
        _write_trend_snapshot(
            category=category,
            source=source,
            ingestion_run=ingestion_run,
            normalized_items=normalized_items,
        )
    except Exception as exc:
        logger.exception("Ingestion failed for category=%s source=%s", category.slug, source)
        ingestion_run.status = IngestionRun.STATUS_FAILED
        ingestion_run.error_message = str(exc)
        ingestion_run.completed_at = timezone.now()
        ingestion_run.save(update_fields=["status", "error_message", "completed_at"])
        return False

    ingestion_run.status = IngestionRun.STATUS_SUCCESS
    ingestion_run.items_fetched = len(normalized_items)
    ingestion_run.error_message = None
    ingestion_run.completed_at = timezone.now()
    ingestion_run.save(
        update_fields=["status", "items_fetched", "error_message", "completed_at"]
    )
    return True


@transaction.atomic
def _write_trend_snapshot(
    *,
    category: Category,
    source: str,
    ingestion_run: IngestionRun,
    normalized_items: list[NormalizedTrendItem],
) -> None:
    snapshot = TrendSnapshot.objects.create(
        category=category,
        ingestion_run=ingestion_run,
        source=source,
    )
    TrendItem.objects.bulk_create(
        [
            TrendItem(
                snapshot=snapshot,
                source=source,
                title=item.title,
                url=item.url,
                external_url=item.external_url,
                score=item.score,
                score_label=item.score_label,
                rank=item.rank,
            )
            for item in normalized_items
        ]
    )


def _record_unknown_source(category: Category, source: str) -> None:
    logger.error("No adapter registered for category=%s source=%s", category.slug, source)
    IngestionRun.objects.create(
        category=category,
        source_adapter=source,
        status=IngestionRun.STATUS_FAILED,
        error_message=f"No adapter registered for source '{source}'",
        completed_at=timezone.now(),
    )
