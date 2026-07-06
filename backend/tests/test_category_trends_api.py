from __future__ import annotations

import pytest
from django.test import Client
from django.utils import timezone

from apps.categories.models import Category, CategorySourceConfig
from apps.ingestion.models import IngestionRun
from apps.trends.models import TrendItem, TrendSnapshot


@pytest.mark.django_db
def test_category_trends_returns_paginated_top_100_items() -> None:
    category = Category.objects.create(name="Tech", slug="tech")
    CategorySourceConfig.objects.create(category=category, source="hackernews")
    snapshot = _create_successful_snapshot(category=category, source="hackernews")

    for index in range(105):
        TrendItem.objects.create(
            snapshot=snapshot,
            source="hackernews",
            title=f"Story {index + 1}",
            url=f"https://news.ycombinator.com/item?id={index + 1}",
            external_url=f"https://example.com/{index + 1}",
            score=200 - index,
            score_label="points",
            rank=index + 1,
        )

    response = Client().get("/api/v1/categories/tech/trends/?page=10&page_size=10")

    assert response.status_code == 200
    payload = response.json()
    assert payload["slug"] == "tech"
    assert payload["pagination"] == {
        "page": 10,
        "page_size": 10,
        "total_items": 100,
        "total_pages": 10,
        "max_items": 100,
    }
    assert len(payload["items"]) == 10
    assert payload["items"][0]["title"] == "Story 91"
    assert payload["items"][0]["source"] == "hackernews"


@pytest.mark.django_db
def test_category_trends_can_filter_to_one_source() -> None:
    category = Category.objects.create(name="Tech", slug="tech")
    CategorySourceConfig.objects.create(category=category, source="hackernews")
    CategorySourceConfig.objects.create(category=category, source="devto")
    hn_snapshot = _create_successful_snapshot(category=category, source="hackernews")
    devto_snapshot = _create_successful_snapshot(category=category, source="devto")

    TrendItem.objects.create(
        snapshot=hn_snapshot,
        source="hackernews",
        title="HN Story",
        url="https://news.ycombinator.com/item?id=1",
        score=500,
        score_label="points",
        rank=1,
    )
    TrendItem.objects.create(
        snapshot=devto_snapshot,
        source="devto",
        title="DEV Article",
        url="https://dev.to/example/dev-article",
        external_url="https://example.com/dev-article",
        score=900,
        score_label="engagement",
        rank=1,
    )

    response = Client().get("/api/v1/categories/tech/trends/?source=devto")

    assert response.status_code == 200
    payload = response.json()
    assert [source["source"] for source in payload["sources"]] == ["devto", "hackernews"]
    assert [item["title"] for item in payload["items"]] == ["DEV Article"]


@pytest.mark.django_db
def test_category_trends_clamps_page_to_last_real_page() -> None:
    category = Category.objects.create(name="Gaming", slug="gaming")
    CategorySourceConfig.objects.create(category=category, source="rawg")
    snapshot = _create_successful_snapshot(category=category, source="rawg")
    TrendItem.objects.create(
        snapshot=snapshot,
        source="rawg",
        title="Hades II",
        url="https://rawg.io/games/hades-ii",
        score=1000,
        score_label="adds",
        rank=1,
    )

    response = Client().get("/api/v1/categories/gaming/trends/?page=99")

    assert response.status_code == 200
    payload = response.json()
    assert payload["pagination"]["page"] == 1
    assert payload["pagination"]["total_pages"] == 1
    assert [item["title"] for item in payload["items"]] == ["Hades II"]


def _create_successful_snapshot(*, category: Category, source: str) -> TrendSnapshot:
    ingestion_run = IngestionRun.objects.create(
        category=category,
        source_adapter=source,
        status=IngestionRun.STATUS_SUCCESS,
        items_fetched=1,
        completed_at=timezone.now(),
    )
    return TrendSnapshot.objects.create(
        category=category,
        ingestion_run=ingestion_run,
        source=source,
    )
