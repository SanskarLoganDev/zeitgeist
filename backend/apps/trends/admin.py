"""
backend/apps/trends/admin.py
──────────────────────────────
Purpose : Registers trend-related models in the Django admin panel.
          The most important admin registration in the whole project — this is
          where staff can see exactly what data the ingestion job produced
          and debug any issues (FR-19).

          What admins can see here:
            - TrendSnapshot: the snapshot records per category per day
            - TrendItem: individual trending posts, with source, score, URL

Used by : Django admin panel — loaded automatically by Django at startup
          Staff users — use this daily to verify ingestion health

Phase    : 1 — Week 2 (register as soon as models exist)
"""
from typing import TYPE_CHECKING, TypeAlias

from django.contrib import admin

from .models import TrendItem, TrendSnapshot

if TYPE_CHECKING:
    TrendSnapshotModelAdmin: TypeAlias = admin.ModelAdmin[TrendSnapshot]  # noqa: UP040
    TrendItemModelAdmin: TypeAlias = admin.ModelAdmin[TrendItem]  # noqa: UP040
else:
    TrendSnapshotModelAdmin = admin.ModelAdmin
    TrendItemModelAdmin = admin.ModelAdmin


@admin.register(TrendSnapshot)
class TrendSnapshotAdmin(TrendSnapshotModelAdmin):
    list_display = ("category", "source", "ingestion_run", "created_at")
    list_filter = ("source", "category", "created_at")
    search_fields = ("category__name", "source")
    autocomplete_fields = ("category", "ingestion_run")
    ordering = ("-created_at",)


@admin.register(TrendItem)
class TrendItemAdmin(TrendItemModelAdmin):
    list_display = ("title", "source", "snapshot", "score", "score_label", "rank", "created_at")
    list_filter = ("source", "score_label", "created_at")
    search_fields = ("title", "url", "external_url")
    autocomplete_fields = ("snapshot",)
    readonly_fields = ("created_at",)
    ordering = ("snapshot", "rank")
