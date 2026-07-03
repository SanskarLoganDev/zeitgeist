"""
Seed starter categories, source mappings, and subreddit mappings.

Run with:
    python manage.py seed_categories
"""
from __future__ import annotations

from typing import TypedDict

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.categories.models import Category, CategorySourceConfig, SubredditConfig


class StarterCategory(TypedDict):
    name: str
    slug: str
    icon: str
    sources: list[str]
    subreddits: list[str]


STARTER_CATEGORIES: list[StarterCategory] = [
    {
        "name": "Tech",
        "slug": "tech",
        "icon": "tech",
        "sources": [
            CategorySourceConfig.SOURCE_HACKERNEWS,
            CategorySourceConfig.SOURCE_REDDIT,
        ],
        "subreddits": ["programming", "technology", "MachineLearning"],
    },
    {
        "name": "Gaming",
        "slug": "gaming",
        "icon": "gaming",
        "sources": [CategorySourceConfig.SOURCE_REDDIT],
        "subreddits": ["gaming", "pcgaming", "Games"],
    },
    {
        "name": "News",
        "slug": "news",
        "icon": "news",
        "sources": [CategorySourceConfig.SOURCE_REDDIT],
        "subreddits": ["news", "worldnews"],
    },
]


class Command(BaseCommand):
    help = "Seed Phase 1 starter categories, source configs, and subreddit configs."

    @transaction.atomic
    def handle(self, *args: object, **options: object) -> None:
        categories_created = 0
        source_configs_created = 0
        subreddit_configs_created = 0

        for category_data in STARTER_CATEGORIES:
            category, created = Category.objects.get_or_create(
                slug=category_data["slug"],
                defaults={
                    "name": category_data["name"],
                    "icon": category_data["icon"],
                    "is_active": True,
                },
            )
            if created:
                categories_created += 1
            else:
                updates: list[str] = []
                if category.name != category_data["name"]:
                    category.name = category_data["name"]
                    updates.append("name")
                if category.icon != category_data["icon"]:
                    category.icon = category_data["icon"]
                    updates.append("icon")
                if not category.is_active:
                    category.is_active = True
                    updates.append("is_active")
                if updates:
                    category.save(update_fields=updates)

            for source in category_data["sources"]:
                _, source_created = CategorySourceConfig.objects.get_or_create(
                    category=category,
                    source=source,
                    defaults={"is_active": True},
                )
                if source_created:
                    source_configs_created += 1

            for subreddit in category_data["subreddits"]:
                _, subreddit_created = SubredditConfig.objects.get_or_create(
                    category=category,
                    subreddit=subreddit,
                    defaults={"is_active": True},
                )
                if subreddit_created:
                    subreddit_configs_created += 1

        self.stdout.write(
            self.style.SUCCESS(
                "Seed complete: "
                f"{categories_created} categories created, "
                f"{source_configs_created} source configs created, "
                f"{subreddit_configs_created} subreddit configs created."
            )
        )
