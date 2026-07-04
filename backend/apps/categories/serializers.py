"""
Serializers for category API responses.
"""
from __future__ import annotations

from rest_framework import serializers

from apps.categories.models import Category, CategorySourceConfig


class CategorySerializer(serializers.ModelSerializer[Category]):
    """Read-only representation of a dashboard category."""

    sources = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "icon", "is_active", "sources"]
        read_only_fields = fields

    def get_sources(self, category: Category) -> list[str]:
        source_configs = getattr(category, "_prefetched_objects_cache", {}).get("source_configs")
        if source_configs is None:
            source_configs = CategorySourceConfig.objects.filter(category=category, is_active=True)

        return [
            source_config.source
            for source_config in source_configs
            if source_config.is_active
        ]
