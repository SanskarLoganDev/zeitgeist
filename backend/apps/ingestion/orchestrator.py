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
            3. For each category, call ai/client.py → Gemini summary

          Key design principle (FR-13):
            Each adapter is isolated in a try/except. One failing source
            (e.g. one API rate-limits) never stops other sources from running.
            The last successful snapshot is always served to users.

Used by : run_job.py — calls orchestrator.run() as the job entrypoint
          apps/trends/views.py (IngestionTriggerView) — admin manual re-trigger

Phase    : 1 — starter ingestion
           Phase 2 — verified sources + Gemini AI processing
"""
from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any, Protocol, TypeAlias

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.ai.client import GeminiClient, SummaryTrendItem
from apps.categories.models import Category
from apps.ingestion.adapters.base import BaseSourceAdapter, NormalizedTrendItem
from apps.ingestion.adapters.devto import DevToAdapter
from apps.ingestion.adapters.football_data import FootballDataAdapter
from apps.ingestion.adapters.hackernews import HackerNewsAdapter
from apps.ingestion.adapters.nytimes import NYTimesMostPopularAdapter
from apps.ingestion.adapters.rawg import RawgAdapter
from apps.ingestion.models import IngestionRun
from apps.trends.models import CategoryAISummary, TrendItem, TrendSnapshot

logger = logging.getLogger(__name__)

SourceAdapter: TypeAlias = BaseSourceAdapter[Any]  # noqa: UP040
AdapterRegistry: TypeAlias = Mapping[str, type[SourceAdapter]]  # noqa: UP040


class CategorySummaryGenerator(Protocol):
    model_name: str

    def generate_category_summary(
        self,
        *,
        category_name: str,
        trend_items: list[SummaryTrendItem],
    ) -> str: ...


ADAPTER_REGISTRY: AdapterRegistry = {
    DevToAdapter.get_source_name(): DevToAdapter,
    FootballDataAdapter.get_source_name(): FootballDataAdapter,
    HackerNewsAdapter.get_source_name(): HackerNewsAdapter,
    NYTimesMostPopularAdapter.get_source_name(): NYTimesMostPopularAdapter,
    RawgAdapter.get_source_name(): RawgAdapter,
}

DEFAULT_ITEM_LIMIT = 50
SUMMARY_ITEMS_PER_SOURCE = 2
SUMMARY_MAX_ITEMS = 5


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
    summary_generator: CategorySummaryGenerator | None = None,
    generate_ai_summaries: bool | None = None,
) -> int:
    """Run ingestion for every active category/source config."""
    had_failure = False
    categories = Category.objects.filter(is_active=True).prefetch_related("source_configs")
    should_generate_ai_summaries = (
        settings.AI_SUMMARIES_ENABLED
        if generate_ai_summaries is None
        else generate_ai_summaries
    )
    category_summary_generator = summary_generator

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
        if should_generate_ai_summaries:
            if category_summary_generator is None:
                category_summary_generator = GeminiClient()
            _generate_category_ai_summary(
                category=category,
                summary_generator=category_summary_generator,
            )

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
                metadata=item.metadata,
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


def _generate_category_ai_summary(
    *,
    category: Category,
    summary_generator: CategorySummaryGenerator,
) -> None:
    trend_items, snapshot_ids = _summary_input_items(category)
    if not trend_items:
        logger.info("Skipping AI summary for category=%s because it has no items", category.slug)
        return

    try:
        summary_text = summary_generator.generate_category_summary(
            category_name=category.name,
            trend_items=trend_items,
        )
    except Exception:
        logger.exception("AI summary generation failed for category=%s", category.slug)
        return

    CategoryAISummary.objects.create(
        category=category,
        summary_text=summary_text,
        model_name=summary_generator.model_name,
        input_item_count=len(trend_items),
        metadata={"snapshot_ids": snapshot_ids},
    )


def _summary_input_items(category: Category) -> tuple[list[SummaryTrendItem], list[int]]:
    source_configs = category.source_configs.filter(is_active=True).order_by("source")
    trend_items: list[SummaryTrendItem] = []
    snapshot_ids: list[int] = []

    for source_config in source_configs:
        snapshot = (
            TrendSnapshot.objects.filter(category=category, source=source_config.source)
            .order_by("-created_at")
            .first()
        )
        if snapshot is None:
            continue

        snapshot_ids.append(snapshot.id)
        for item in snapshot.items.order_by("rank")[:SUMMARY_ITEMS_PER_SOURCE]:
            trend_items.append(
                SummaryTrendItem(
                    source=source_config.source,
                    rank=item.rank,
                    title=item.title,
                    score_label=f"{item.score} {item.score_label}",
                    metadata=item.metadata,
                )
            )

    return trend_items[:SUMMARY_MAX_ITEMS], snapshot_ids
