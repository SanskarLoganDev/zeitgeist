from collections.abc import Mapping
from datetime import timedelta
from typing import Any

import pytest
from django.utils import timezone

from apps.categories.models import Category
from apps.ingestion.adapters.rawg import RawgAdapter


class FakeResponse:
    def __init__(self, payload: object) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> object:
        return self.payload


class FakeSession:
    def __init__(self, payload: object) -> None:
        self.payload = payload
        self.requested_url: str | None = None
        self.requested_kwargs: dict[str, Any] = {}

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        self.requested_url = url
        self.requested_kwargs = kwargs
        return FakeResponse(self.payload)


def test_fetch_returns_valid_rawg_games_only() -> None:
    payload: Mapping[str, object] = {
        "count": 3,
        "results": [
            {
                "id": 3498,
                "slug": "grand-theft-auto-v",
                "name": "Grand Theft Auto V",
                "added": 23000,
                "ratings_count": 7200,
                "released": "2013-09-17",
                "background_image": "https://media.rawg.io/media/games/example.jpg",
            },
            {
                "id": 3499,
                "slug": "",
                "name": "Missing Slug",
            },
            {
                "id": 3500,
                "slug": "missing-name",
            },
        ],
    }
    session = FakeSession(payload)
    adapter = RawgAdapter(session=session, api_key="test-key")
    category = Category(name="Gaming", slug="gaming")

    items = adapter.fetch(category=category, limit=5)

    today = timezone.localdate()
    assert len(items) == 1
    assert items[0]["id"] == 3498
    assert items[0]["name"] == "Grand Theft Auto V"
    assert session.requested_url == RawgAdapter.games_url
    assert session.requested_kwargs["params"] == {
        "key": "test-key",
        "dates": (
            f"{(today - timedelta(days=365)).isoformat()},"
            f"{(today + timedelta(days=90)).isoformat()}"
        ),
        "ordering": "-added",
        "page_size": 5,
    }


def test_fetch_requires_api_key() -> None:
    adapter = RawgAdapter(session=FakeSession({"results": []}), api_key="")
    category = Category(name="Gaming", slug="gaming")

    with pytest.raises(RuntimeError, match="RAWG_API_KEY is required"):
        adapter.fetch(category=category)


def test_normalise_uses_rawg_added_score() -> None:
    adapter = RawgAdapter(session=FakeSession({}), api_key="test-key")
    category = Category(name="Gaming", slug="gaming")

    item = adapter.normalise(
        {
            "id": 3498,
            "slug": "grand-theft-auto-v",
            "name": "Grand Theft Auto V",
            "added": 23000,
            "ratings_count": 7200,
        },
        category=category,
        rank=2,
    )

    assert item.title == "Grand Theft Auto V"
    assert item.url == "https://rawg.io/games/grand-theft-auto-v"
    assert item.external_url == "https://rawg.io/games/grand-theft-auto-v"
    assert item.score == 23000
    assert item.score_label == "adds"
    assert item.rank == 2


def test_normalise_falls_back_to_ratings_count() -> None:
    adapter = RawgAdapter(session=FakeSession({}), api_key="test-key")
    category = Category(name="Gaming", slug="gaming")

    item = adapter.normalise(
        {
            "id": 3498,
            "slug": "grand-theft-auto-v",
            "name": "Grand Theft Auto V",
            "ratings_count": 7200,
        },
        category=category,
        rank=1,
    )

    assert item.score == 7200
    assert item.score_label == "ratings"
