from collections.abc import Mapping
from typing import Any

from apps.categories.models import Category
from apps.ingestion.adapters.devto import DevToAdapter


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


def test_fetch_returns_valid_dev_articles_only() -> None:
    payload: list[Mapping[str, object]] = [
        {
            "id": 4017704,
            "title": "My Next.js 16 Auth Passed Every Test",
            "url": "https://dev.to/shubhradev/my-nextjs-16-auth-passed-every-test",
            "canonical_url": "https://dev.to/shubhradev/my-nextjs-16-auth-passed-every-test",
            "public_reactions_count": 34,
            "comments_count": 22,
            "tag_list": ["nextjs", "security", "webdev", "javascript"],
        },
        {
            "id": 4017705,
            "title": "",
            "url": "https://dev.to/invalid/blank-title",
        },
        {
            "id": 4017706,
            "title": "Missing URL",
        },
    ]
    session = FakeSession(payload)
    adapter = DevToAdapter(session=session)
    category = Category(name="Tech", slug="tech")

    items = adapter.fetch(category=category, limit=5)

    assert len(items) == 1
    assert items[0]["id"] == 4017704
    assert items[0]["title"] == "My Next.js 16 Auth Passed Every Test"
    assert session.requested_url == DevToAdapter.articles_url
    assert session.requested_kwargs["params"] == {
        "top": 7,
        "tags": "javascript,webdev,ai,programming,security",
        "per_page": 5,
    }


def test_normalise_uses_dev_engagement_score() -> None:
    adapter = DevToAdapter(session=FakeSession([]))
    category = Category(name="Tech", slug="tech")

    item = adapter.normalise(
        {
            "id": 4017704,
            "title": "My Next.js 16 Auth Passed Every Test",
            "url": "https://dev.to/shubhradev/my-nextjs-16-auth-passed-every-test",
            "canonical_url": "https://example.com/original",
            "public_reactions_count": 34,
            "comments_count": 22,
        },
        category=category,
        rank=2,
    )

    assert item.title == "My Next.js 16 Auth Passed Every Test"
    assert item.url == "https://dev.to/shubhradev/my-nextjs-16-auth-passed-every-test"
    assert item.external_url == "https://example.com/original"
    assert item.score == 56
    assert item.score_label == "engagement"
    assert item.rank == 2


def test_fetch_and_normalise_falls_back_to_dev_url_for_external_url() -> None:
    payload = [
        {
            "id": 4017704,
            "title": "My Next.js 16 Auth Passed Every Test",
            "url": "https://dev.to/shubhradev/my-nextjs-16-auth-passed-every-test",
            "public_reactions_count": 34,
            "comments_count": 22,
        },
    ]
    adapter = DevToAdapter(session=FakeSession(payload))
    category = Category(name="Tech", slug="tech")

    items = adapter.fetch_and_normalise(category=category, limit=1)

    assert len(items) == 1
    assert items[0].external_url == "https://dev.to/shubhradev/my-nextjs-16-auth-passed-every-test"
    assert items[0].score == 56
    assert items[0].rank == 1
