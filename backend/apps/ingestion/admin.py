"""
backend/apps/ingestion/admin.py
─────────────────────────────────
Purpose : Registers the IngestionRun model in Django admin.
          This is the primary operational dashboard for monitoring the
          health of the daily ingestion pipeline (FR-19).

          What admins see and can do:
            - View all ingestion run records: source, category, status,
              items fetched, error message, start/end timestamps
            - Filter by status (success/failed) and date
            - Search by source adapter name
            - Manually trigger a re-fetch by calling IngestionTriggerView

Used by : Django admin panel — loaded automatically at startup
          Staff users — check this after every nightly run to confirm health

Phase    : 1 — Week 2
"""
from typing import TYPE_CHECKING, TypeAlias

from django.contrib import admin

from .models import IngestionRun

if TYPE_CHECKING:
    IngestionRunModelAdmin: TypeAlias = admin.ModelAdmin[IngestionRun]  # noqa: UP040
else:
    IngestionRunModelAdmin = admin.ModelAdmin


@admin.register(IngestionRun)
class IngestionRunAdmin(IngestionRunModelAdmin):
    list_display = (
        "category",
        "source_adapter",
        "status",
        "items_fetched",
        "started_at",
        "completed_at",
        "duration_seconds",
    )
    list_filter = ("status", "source_adapter", "category", "started_at")
    search_fields = ("source_adapter", "category__name", "error_message")
    readonly_fields = ("started_at", "completed_at", "duration_seconds")
    ordering = ("-started_at",)
