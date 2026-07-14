import pytest
from django.core.management import call_command

from apps.categories.models import Category, CategorySourceConfig


@pytest.mark.django_db
def test_seed_categories_maps_tech_to_hackernews_and_devto() -> None:
    call_command("seed_categories")

    tech = Category.objects.get(slug="tech")
    sources = set(
        CategorySourceConfig.objects.filter(category=tech).values_list("source", flat=True)
    )

    assert sources == {
        CategorySourceConfig.SOURCE_HACKERNEWS,
        CategorySourceConfig.SOURCE_DEVTO,
    }


@pytest.mark.django_db
def test_seed_categories_maps_news_to_nytimes() -> None:
    call_command("seed_categories")

    news = Category.objects.get(slug="news")
    sources = set(
        CategorySourceConfig.objects.filter(category=news).values_list("source", flat=True)
    )

    assert sources == {CategorySourceConfig.SOURCE_NYTIMES}


@pytest.mark.django_db
def test_seed_categories_maps_gaming_to_rawg() -> None:
    call_command("seed_categories")

    gaming = Category.objects.get(slug="gaming")
    sources = set(
        CategorySourceConfig.objects.filter(category=gaming).values_list("source", flat=True)
    )

    assert sources == {CategorySourceConfig.SOURCE_RAWG}


@pytest.mark.django_db
def test_seed_categories_removes_inactive_source_configs() -> None:
    tech = Category.objects.create(name="Tech", slug="tech", icon="tech")
    CategorySourceConfig.objects.create(category=tech, source="unused_source")

    call_command("seed_categories")

    assert not CategorySourceConfig.objects.filter(source="unused_source").exists()
