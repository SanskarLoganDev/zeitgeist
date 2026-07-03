from collections.abc import Mapping
from typing import Any

from apps.categories.models import Category
from apps.ingestion.adapters.hackernews import HackerNewsAdapter


class FakeResponse:
    def __init__(self, payload: object) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> object:
        return self.payload


class FakeSession:
    def __init__(self, responses: Mapping[str, object]) -> None:
        self.responses = responses
        self.requested_urls: list[str] = []

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        self.requested_urls.append(url)
        return FakeResponse(self.responses[url])


def test_fetch_returns_valid_hacker_news_stories_only() -> None:
    responses = {
        HackerNewsAdapter.top_stories_url: [101, 102, 103, 104],
        HackerNewsAdapter.item_url_template.format(item_id=101): {
            "id": 101,
            "type": "story",
            "title": "First story",
            "url": "https://example.com/first",
            "score": 42,
        },
        HackerNewsAdapter.item_url_template.format(item_id=102): {
            "id": 102,
            "type": "comment",
            "title": "Not a story",
        },
        HackerNewsAdapter.item_url_template.format(item_id=103): {
            "id": 103,
            "type": "story",
            "deleted": True,
            "title": "Deleted story",
        },
        HackerNewsAdapter.item_url_template.format(item_id=104): {
            "id": 104,
            "type": "story",
            "title": "Second story",
            "score": 7,
        },
    }
    adapter = HackerNewsAdapter(session=FakeSession(responses))
    category = Category(name="Tech", slug="tech")

    items = adapter.fetch(category=category, limit=2)

    assert [item["id"] for item in items] == [101, 104]
    assert [item["title"] for item in items] == ["First story", "Second story"]


def test_normalise_uses_hn_discussion_url_and_external_url() -> None:
    adapter = HackerNewsAdapter(session=FakeSession({}))
    category = Category(name="Tech", slug="tech")

    item = adapter.normalise(
        {
            "id": 101,
            "type": "story",
            "title": "First story",
            "url": "https://example.com/first",
            "score": 42,
        },
        category=category,
        rank=3,
    )

    assert item.title == "First story"
    assert item.url == "https://news.ycombinator.com/item?id=101"
    assert item.external_url == "https://example.com/first"
    assert item.score == 42
    assert item.score_label == "points"
    assert item.rank == 3


def test_fetch_and_normalise_returns_ranked_items() -> None:
    responses = {
        HackerNewsAdapter.top_stories_url: [101],
        HackerNewsAdapter.item_url_template.format(item_id=101): {
            "id": 101,
            "type": "story",
            "title": "First story",
            "score": 42,
        },
    }
    adapter = HackerNewsAdapter(session=FakeSession(responses))
    category = Category(name="Tech", slug="tech")

    items = adapter.fetch_and_normalise(category=category, limit=1)

    assert len(items) == 1
    assert items[0].title == "First story"
    assert items[0].url == "https://news.ycombinator.com/item?id=101"
    assert items[0].external_url is None
    assert items[0].rank == 1
