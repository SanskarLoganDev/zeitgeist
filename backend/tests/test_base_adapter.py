from typing import TypedDict

from apps.categories.models import Category
from apps.ingestion.adapters.base import BaseSourceAdapter, NormalizedTrendItem


class FakeRawItem(TypedDict):
    title: str
    score: int


class FakeAdapter(BaseSourceAdapter[FakeRawItem]):
    @classmethod
    def get_source_name(cls) -> str:
        return "fake"

    def fetch(self, category: Category, *, limit: int = 50) -> list[FakeRawItem]:
        return [
            {"title": f"Item {index}", "score": 100 - index}
            for index in range(1, limit + 1)
        ]

    def normalise(
        self,
        raw_item: FakeRawItem,
        category: Category,
        *,
        rank: int,
    ) -> NormalizedTrendItem:
        return NormalizedTrendItem(
            title=raw_item["title"],
            url=f"https://example.com/{rank}",
            external_url=None,
            score=raw_item["score"],
            score_label="points",
            rank=rank,
        )


def test_fetch_and_normalise_assigns_one_based_rank() -> None:
    adapter = FakeAdapter()
    category = Category(name="Tech", slug="tech")

    items = adapter.fetch_and_normalise(category=category, limit=3)

    assert [item.rank for item in items] == [1, 2, 3]
    assert [item.title for item in items] == ["Item 1", "Item 2", "Item 3"]
