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
def test_seed_categories_removes_deprecated_reddit_source_configs() -> None:
    tech = Category.objects.create(name="Tech", slug="tech", icon="tech")
    CategorySourceConfig.objects.create(category=tech, source="reddit")

    call_command("seed_categories")

    assert not CategorySourceConfig.objects.filter(source="reddit").exists()
