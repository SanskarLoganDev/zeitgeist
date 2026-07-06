import pytest

from apps.categories.models import Category, CategorySourceConfig
from apps.ingestion.adapters.base import BaseSourceAdapter, NormalizedTrendItem
from apps.ingestion.models import IngestionRun
from apps.ingestion.orchestrator import run_with_adapters
from apps.trends.models import TrendItem, TrendSnapshot


class SuccessfulAdapter(BaseSourceAdapter[dict[str, str]]):
    @classmethod
    def get_source_name(cls) -> str:
        return "successful"

    def fetch(self, category: Category, *, limit: int = 50) -> list[dict[str, str]]:
        return [{"title": "First story"}, {"title": "Second story"}][:limit]

    def normalise(
        self,
        raw_item: dict[str, str],
        category: Category,
        *,
        rank: int,
    ) -> NormalizedTrendItem:
        return NormalizedTrendItem(
            title=raw_item["title"],
            url=f"https://news.ycombinator.com/item?id={rank}",
            external_url=f"https://example.com/{rank}",
            score=100 - rank,
            score_label="points",
            rank=rank,
        )


class FailingAdapter(BaseSourceAdapter[dict[str, str]]):
    @classmethod
    def get_source_name(cls) -> str:
        return "failing"

    def fetch(self, category: Category, *, limit: int = 50) -> list[dict[str, str]]:
        raise RuntimeError("external API unavailable")

    def normalise(
        self,
        raw_item: dict[str, str],
        category: Category,
        *,
        rank: int,
    ) -> NormalizedTrendItem:
        raise AssertionError("normalise should not be called when fetch fails")


@pytest.mark.django_db
def test_run_with_adapters_writes_successful_ingestion_rows() -> None:
    category = Category.objects.create(name="Tech", slug="tech")
    CategorySourceConfig.objects.create(category=category, source="successful")

    exit_code = run_with_adapters({"successful": SuccessfulAdapter}, item_limit=2)

    assert exit_code == 0

    ingestion_run = IngestionRun.objects.get()
    assert ingestion_run.category == category
    assert ingestion_run.source_adapter == "successful"
    assert ingestion_run.status == IngestionRun.STATUS_SUCCESS
    assert ingestion_run.items_fetched == 2
    assert ingestion_run.error_message is None
    assert ingestion_run.completed_at is not None

    snapshot = TrendSnapshot.objects.get()
    assert snapshot.category == category
    assert snapshot.ingestion_run == ingestion_run
    assert snapshot.source == "successful"

    trend_items = list(TrendItem.objects.order_by("rank"))
    assert [item.title for item in trend_items] == ["First story", "Second story"]
    assert [item.rank for item in trend_items] == [1, 2]
    assert [item.score_label for item in trend_items] == ["points", "points"]


@pytest.mark.django_db
def test_run_with_adapters_records_failure_and_continues() -> None:
    category = Category.objects.create(name="Tech", slug="tech")
    CategorySourceConfig.objects.create(category=category, source="failing")
    CategorySourceConfig.objects.create(category=category, source="successful")

    exit_code = run_with_adapters(
        {
            "failing": FailingAdapter,
            "successful": SuccessfulAdapter,
        },
        item_limit=1,
    )

    assert exit_code == 1

    failed_run = IngestionRun.objects.get(source_adapter="failing")
    assert failed_run.status == IngestionRun.STATUS_FAILED
    assert failed_run.items_fetched == 0
    assert failed_run.error_message == "external API unavailable"
    assert failed_run.completed_at is not None

    successful_run = IngestionRun.objects.get(source_adapter="successful")
    assert successful_run.status == IngestionRun.STATUS_SUCCESS
    assert successful_run.items_fetched == 1
    assert TrendItem.objects.count() == 1


@pytest.mark.django_db
def test_run_with_adapters_records_unknown_source_as_failure() -> None:
    category = Category.objects.create(name="Tech", slug="tech")
    CategorySourceConfig.objects.create(category=category, source="unknown")

    exit_code = run_with_adapters({}, item_limit=1)

    assert exit_code == 1

    ingestion_run = IngestionRun.objects.get()
    assert ingestion_run.status == IngestionRun.STATUS_FAILED
    assert ingestion_run.source_adapter == "unknown"
    assert ingestion_run.error_message == "No adapter registered for source 'unknown'"
    assert ingestion_run.completed_at is not None
    assert TrendSnapshot.objects.count() == 0
    assert TrendItem.objects.count() == 0
