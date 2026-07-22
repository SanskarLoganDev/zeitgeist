from __future__ import annotations

import pytest
from django.core.management import call_command

from apps.categories.models import Category, CategorySourceConfig


@pytest.mark.django_db
def test_seed_categories_creates_sports_with_active_sports_sources() -> None:
    call_command("seed_categories")

    sports = Category.objects.get(slug="sports")
    assert sports.name == "Sports"
    assert sports.icon == "sports"
    assert set(
        CategorySourceConfig.objects.filter(category=sports, is_active=True).values_list(
            "source",
            flat=True,
        )
    ) == {
        CategorySourceConfig.SOURCE_FOOTBALL_DATA,
        CategorySourceConfig.SOURCE_CRICKET_DATA,
    }
