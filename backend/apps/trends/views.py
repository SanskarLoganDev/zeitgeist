"""
backend/apps/trends/views.py
──────────────────────────────
Purpose : DRF API views for the dashboard and ingestion admin endpoints.

          Views:
            DashboardView         GET /api/v1/dashboard/
              The main view users see on login. Returns the top 5 TrendItems per
              category for all categories the user has selected in preferences.
              Phase 1: returns all 3 starter categories for all users (no personalisation).
              Phase 2: filtered by UserCategoryPreference, served from Redis cache.

            IngestionRunListView  GET /api/v1/admin/ingestion/runs/
              Staff-only. Returns the full history of IngestionRun records —
              source, status, items_fetched, error_message, timestamps.
              Displayed in the Django admin panel and accessible via the API
              for future monitoring integrations.

            IngestionTriggerView  POST /api/v1/admin/ingestion/trigger/
              Staff-only. Manually triggers an ingestion run for a specific source.
              Used during development and when a run fails and needs a re-fetch (FR-19).

Used by : apps/trends/urls.py    — routes requests to these views
          Next.js frontend       — DashboardView is the first page after login
          Django admin           — IngestionRunListView powers the log display

Phase    : 1 Week 3 — DashboardView (basic, no cache, all categories)
           Phase 2   — DashboardView with Redis cache + preference filtering
           Phase 1 Week 2 — IngestionRunListView, IngestionTriggerView
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.db.models import QuerySet
from django.http import Http404
from django.utils import timezone
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.categories.models import Category, CategorySourceConfig
from apps.ingestion.models import IngestionRun
from apps.trends.models import TrendItem, TrendSnapshot
from apps.trends.serializers import TrendItemSerializer

DEFAULT_ITEM_LIMIT = 20
MAX_ITEM_LIMIT = 50
FRESHNESS_WINDOW = timedelta(hours=25)


class DashboardView(APIView):
    """
    Return the latest stored trends grouped by active category and source.

    Phase 1 intentionally returns every active category for every user. Phase 2
    can filter this by UserCategoryPreference once auth/personalisation is live.
    """

    def get(self, request: Request) -> Response:
        categories = (
            Category.objects.filter(is_active=True)
            .prefetch_related("source_configs")
            .order_by("name")
        )

        return Response(
            {
                "categories": [
                    _build_category_payload(category, limit=DEFAULT_ITEM_LIMIT)
                    for category in categories
                ]
            }
        )


class CategoryTrendsView(APIView):
    """Return latest stored trends for one active category."""

    def get(self, request: Request, slug: str) -> Response:
        category = _get_active_category(slug)
        source = request.query_params.get("source")
        limit = _parse_limit(request.query_params.get("limit"))

        return Response(
            _build_category_payload(
                category,
                source_filter=source,
                limit=limit,
            )
        )


def _get_active_category(slug: str) -> Category:
    try:
        return (
            Category.objects.prefetch_related("source_configs")
            .filter(is_active=True)
            .get(slug=slug)
        )
    except Category.DoesNotExist as exc:
        raise Http404("Category not found") from exc


def _parse_limit(raw_limit: str | None) -> int:
    if raw_limit is None:
        return DEFAULT_ITEM_LIMIT

    try:
        parsed_limit = int(raw_limit)
    except ValueError:
        return DEFAULT_ITEM_LIMIT

    if parsed_limit < 1:
        return DEFAULT_ITEM_LIMIT
    return min(parsed_limit, MAX_ITEM_LIMIT)


def _build_category_payload(
    category: Category,
    *,
    source_filter: str | None = None,
    limit: int,
) -> dict[str, Any]:
    source_configs = _active_source_configs(category)
    if source_filter is not None:
        source_configs = [
            source_config
            for source_config in source_configs
            if source_config.source == source_filter
        ]

    return {
        "id": category.id,
        "name": category.name,
        "slug": category.slug,
        "icon": category.icon,
        "sources": [
            _build_source_payload(
                category=category,
                source=source_config.source,
                limit=limit,
            )
            for source_config in source_configs
        ],
    }


def _active_source_configs(category: Category) -> list[CategorySourceConfig]:
    source_configs = getattr(category, "_prefetched_objects_cache", {}).get("source_configs")
    if source_configs is None:
        source_configs = CategorySourceConfig.objects.filter(category=category, is_active=True)

    return [
        source_config
        for source_config in source_configs
        if source_config.is_active
    ]


def _build_source_payload(
    *,
    category: Category,
    source: str,
    limit: int,
) -> dict[str, Any]:
    snapshot = _latest_snapshot(category=category, source=source)
    ingestion_run = _latest_successful_run(category=category, source=source)

    items: QuerySet[TrendItem] | list[TrendItem]
    if snapshot is None:
        items = []
    else:
        items = snapshot.items.order_by("rank")[:limit]

    return {
        "source": source,
        "last_updated": (
            ingestion_run.completed_at.isoformat()
            if ingestion_run is not None and ingestion_run.completed_at is not None
            else None
        ),
        "status": _freshness_status(ingestion_run),
        "items": TrendItemSerializer(items, many=True).data,
    }


def _latest_snapshot(*, category: Category, source: str) -> TrendSnapshot | None:
    return (
        TrendSnapshot.objects.filter(category=category, source=source)
        .select_related("ingestion_run")
        .order_by("-created_at")
        .first()
    )


def _latest_successful_run(*, category: Category, source: str) -> IngestionRun | None:
    return (
        IngestionRun.objects.filter(
            category=category,
            source_adapter=source,
            status=IngestionRun.STATUS_SUCCESS,
        )
        .order_by("-completed_at", "-started_at")
        .first()
    )


def _freshness_status(ingestion_run: IngestionRun | None) -> str:
    if ingestion_run is None or ingestion_run.completed_at is None:
        return "missing"

    if ingestion_run.completed_at < timezone.now() - FRESHNESS_WINDOW:
        return "stale"

    return "fresh"
