import pytest

from apps.categories.models import Category, CategorySourceConfig
from apps.ingestion.adapters.base import BaseSourceAdapter, NormalizedTrendItem
from apps.ingestion.models import IngestionRun
from apps.ingestion.orchestrator import run_with_adapters
from apps.trends.models import TrendItem, TrendSnapshot


class SuccessfulAdapter(BaseSourceAdapter[dict[str, object]]):
    @classmethod
    def get_source_name(cls) -> str:
        return "successful_source"

    def fetch(self, category: Category, *, limit: int = 50) -> list[dict[str, object]]:
        del category, limit
        return [{"title": "A working source"}]

    def normalise(
        self,
        raw_item: dict[str, object],
        category: Category,
        *,
        rank: int,
    ) -> NormalizedTrendItem:
        del category
        return NormalizedTrendItem(
            title=str(raw_item["title"]),
            url="https://example.com/item",
            external_url="https://example.com/item",
            score=10,
            score_label="points",
            rank=rank,
        )


class FailingAdapter(BaseSourceAdapter[dict[str, object]]):
    @classmethod
    def get_source_name(cls) -> str:
        return "failing_source"

    def fetch(self, category: Category, *, limit: int = 50) -> list[dict[str, object]]:
        del category, limit
        raise TimeoutError("source timed out")

    def normalise(
        self,
        raw_item: dict[str, object],
        category: Category,
        *,
        rank: int,
    ) -> NormalizedTrendItem:
        raise AssertionError("normalise should not be called after fetch fails")


@pytest.mark.django_db
def test_source_failure_is_recorded_without_failing_entire_batch() -> None:
    category = Category.objects.create(name="Gaming", slug="gaming", is_active=True)
    CategorySourceConfig.objects.create(
        category=category,
        source=SuccessfulAdapter.get_source_name(),
        is_active=True,
    )
    CategorySourceConfig.objects.create(
        category=category,
        source=FailingAdapter.get_source_name(),
        is_active=True,
    )

    exit_code = run_with_adapters(
        {
            SuccessfulAdapter.get_source_name(): SuccessfulAdapter,
            FailingAdapter.get_source_name(): FailingAdapter,
        },
        generate_ai_summaries=False,
    )

    assert exit_code == 0
    assert TrendSnapshot.objects.filter(category=category, source="successful_source").exists()
    assert TrendItem.objects.filter(source="successful_source", title="A working source").exists()

    failed_run = IngestionRun.objects.get(category=category, source_adapter="failing_source")
    assert failed_run.status == IngestionRun.STATUS_FAILED
    assert failed_run.error_message == "source timed out"
