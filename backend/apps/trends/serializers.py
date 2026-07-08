"""
Serializers for trend API responses.
"""
from __future__ import annotations

from rest_framework import serializers

from apps.trends.models import TrendItem


class TrendItemSerializer(serializers.ModelSerializer[TrendItem]):
    """Read-only trend card payload consumed by the frontend."""

    class Meta:
        model = TrendItem
        fields = [
            "source",
            "rank",
            "title",
            "url",
            "external_url",
            "score",
            "score_label",
            "metadata",
            "ai_summary",
            "sentiment",
        ]
        read_only_fields = fields
