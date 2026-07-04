from __future__ import annotations

from datetime import timedelta

import pytest
from django.test import Client
from django.utils import timezone

from apps.categories.models import Category, CategorySourceConfig
from apps.ingestion.models import IngestionRun
from apps.trends.models import TrendItem, TrendSnapshot


@pytest.fixture
def api_client() -> Client:
    return Client()


@pytest.fixture
def tech_category() -> Category:
    return Category.objects.create(name="Tech", slug="tech", icon="tech", is_active=True)


@pytest.fixture
def hackernews_config(tech_category: Category) -> CategorySourceConfig:
    return CategorySourceConfig.objects.create(
        category=tech_category,
        source=CategorySourceConfig.SOURCE_HACKERNEWS,
        is_active=True,
    )


@pytest.fixture
def hackernews_snapshot(
    tech_category: Category,
    hackernews_config: CategorySourceConfig,
) -> TrendSnapshot:
    del hackernews_config
    ingestion_run = IngestionRun.objects.create(
        category=tech_category,
        source_adapter=CategorySourceConfig.SOURCE_HACKERNEWS,
        status=IngestionRun.STATUS_SUCCESS,
        items_fetched=2,
        completed_at=timezone.now(),
    )
    snapshot = TrendSnapshot.objects.create(
        category=tech_category,
        source=CategorySourceConfig.SOURCE_HACKERNEWS,
        ingestion_run=ingestion_run,
    )
    TrendItem.objects.create(
        snapshot=snapshot,
        source=CategorySourceConfig.SOURCE_HACKERNEWS,
        title="SQLite on the server",
        url="https://news.ycombinator.com/item?id=1",
        external_url="https://example.com/sqlite",
        score=512,
        score_label="points",
        rank=1,
    )
    TrendItem.objects.create(
        snapshot=snapshot,
        source=CategorySourceConfig.SOURCE_HACKERNEWS,
        title="A useful debugger story",
        url="https://news.ycombinator.com/item?id=2",
        external_url="https://example.com/debugger",
        score=250,
        score_label="points",
        rank=2,
    )
    return snapshot


@pytest.mark.django_db
def test_category_list_returns_active_categories_with_sources(
    api_client: Client,
    tech_category: Category,
    hackernews_config: CategorySourceConfig,
) -> None:
    del hackernews_config
    Category.objects.create(name="Hidden", slug="hidden", is_active=False)

    response = api_client.get("/api/v1/categories/")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": tech_category.id,
            "name": "Tech",
            "slug": "tech",
            "icon": "tech",
            "is_active": True,
            "sources": ["hackernews"],
        }
    ]


@pytest.mark.django_db
def test_dashboard_returns_latest_hackernews_items(
    api_client: Client,
    hackernews_snapshot: TrendSnapshot,
) -> None:
    del hackernews_snapshot

    response = api_client.get("/api/v1/dashboard/")

    assert response.status_code == 200
    payload = response.json()
    tech = payload["categories"][0]
    source = tech["sources"][0]

    assert tech["slug"] == "tech"
    assert source["source"] == "hackernews"
    assert source["status"] == "fresh"
    assert len(source["items"]) == 2
    assert source["items"][0]["rank"] == 1
    assert source["items"][0]["title"] == "SQLite on the server"
    assert source["items"][0]["score_label"] == "points"


@pytest.mark.django_db
def test_category_trends_supports_limit_query_param(
    api_client: Client,
    hackernews_snapshot: TrendSnapshot,
) -> None:
    del hackernews_snapshot

    response = api_client.get("/api/v1/categories/tech/trends/?limit=1")

    assert response.status_code == 200
    source = response.json()["sources"][0]
    assert len(source["items"]) == 1
    assert source["items"][0]["rank"] == 1


@pytest.mark.django_db
def test_category_trends_returns_404_for_unknown_category(api_client: Client) -> None:
    response = api_client.get("/api/v1/categories/unknown/trends/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_dashboard_marks_old_successful_run_as_stale(
    api_client: Client,
    hackernews_snapshot: TrendSnapshot,
) -> None:
    ingestion_run = hackernews_snapshot.ingestion_run
    ingestion_run.completed_at = timezone.now() - timedelta(hours=26)
    ingestion_run.save(update_fields=["completed_at"])

    response = api_client.get("/api/v1/dashboard/")

    assert response.status_code == 200
    source = response.json()["categories"][0]["sources"][0]
    assert source["status"] == "stale"
