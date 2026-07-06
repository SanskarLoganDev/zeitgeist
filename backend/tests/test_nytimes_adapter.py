from collections.abc import Mapping
from typing import Any

import pytest

from apps.categories.models import Category
from apps.ingestion.adapters.nytimes import NYTimesMostPopularAdapter


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


def test_fetch_returns_valid_nytimes_articles_only() -> None:
    payload: Mapping[str, object] = {
        "status": "OK",
        "results": [
            {
                "id": 100000010,
                "title": "A Major Story Everyone Is Reading",
                "url": "https://www.nytimes.com/2026/07/06/world/major-story.html",
                "abstract": "A short summary.",
                "published_date": "2026-07-06",
            },
            {
                "id": 100000011,
                "title": "",
                "url": "https://www.nytimes.com/invalid/blank-title.html",
            },
            {
                "id": 100000012,
                "title": "Missing URL",
            },
        ],
    }
    session = FakeSession(payload)
    adapter = NYTimesMostPopularAdapter(session=session, api_key="test-key")
    category = Category(name="News", slug="news")

    items = adapter.fetch(category=category, limit=5)

    assert len(items) == 1
    assert items[0]["id"] == 100000010
    assert items[0]["title"] == "A Major Story Everyone Is Reading"
    assert session.requested_url == (
        "https://api.nytimes.com/svc/mostpopular/v2/viewed/30.json"
    )
    assert session.requested_kwargs["params"] == {"api-key": "test-key"}


def test_fetch_requires_api_key() -> None:
    adapter = NYTimesMostPopularAdapter(session=FakeSession({"results": []}), api_key="")
    category = Category(name="News", slug="news")

    with pytest.raises(RuntimeError, match="NYTIMES_API_KEY is required"):
        adapter.fetch(category=category)


def test_normalise_uses_rank_derived_most_viewed_score() -> None:
    adapter = NYTimesMostPopularAdapter(session=FakeSession({}), api_key="test-key")
    category = Category(name="News", slug="news")

    item = adapter.normalise(
        {
            "id": 100000010,
            "title": "A Major Story Everyone Is Reading",
            "url": "https://www.nytimes.com/2026/07/06/world/major-story.html",
        },
        category=category,
        rank=3,
    )

    assert item.title == "A Major Story Everyone Is Reading"
    assert item.url == "https://www.nytimes.com/2026/07/06/world/major-story.html"
    assert item.external_url == "https://www.nytimes.com/2026/07/06/world/major-story.html"
    assert item.score == 97
    assert item.score_label == "most viewed"
    assert item.rank == 3
