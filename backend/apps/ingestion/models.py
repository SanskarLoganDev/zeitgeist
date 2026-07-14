"""
backend/apps/ingestion/models.py
──────────────────────────────────
Purpose : Defines the IngestionRun model — the audit log for every ingestion attempt.

          IngestionRun
            One record is written per source adapter per daily run.
            If there are 3 categories × 2 sources, that's 6 records
            written after each run.

            Fields:
              source_adapter  : which adapter ran — "hackernews", "devto", etc.
              category        : which category this run served
              status          : "success" | "partial" | "failed"
              items_fetched   : how many TrendItems were written
              error_message   : null on success, exception message on failure
              started_at      : when the adapter began fetching
              completed_at    : when it finished (or failed)

            This powers:
              - Django admin ingestion log (FR-19)
              - The stale data indicator on category pages (FR-13) — the frontend
                reads last_updated from the most recent successful IngestionRun
                for that category
              - Phase 3: Cloud Monitoring alert if no successful run in 25+ hours

Used by : apps/ingestion/orchestrator.py — creates and updates IngestionRun records
          apps/trends/views.py           — reads latest run timestamp for stale indicator
          apps/trends/admin.py           — displays run history in Django admin
          apps/trends/views.py (admin)   — IngestionRunListView returns run history via API

Phase    : 1 — Week 2
"""
from django.db import models


class IngestionRun(models.Model):
    """
    Audit log for every ingestion attempt — one record per source adapter per run.

    The orchestrator creates an IngestionRun at the start of each adapter call,
    updates it on completion (success or failure), and moves on to the next adapter
    regardless. This ensures one failing source never blocks others (FR-13).

    Admin staff check this table daily to verify ingestion health (FR-19).
    The dashboard API reads the most recent successful run per category to
    produce the "last updated X hours ago" stale data indicator (FR-13).
    """

    STATUS_RUNNING = "running"
    STATUS_SUCCESS = "success"
    STATUS_PARTIAL = "partial"   # some items fetched but not all
    STATUS_FAILED = "failed"

    STATUS_CHOICES = [
        (STATUS_RUNNING, "Running"),
        (STATUS_SUCCESS, "Success"),
        (STATUS_PARTIAL, "Partial"),
        (STATUS_FAILED, "Failed"),
    ]

    # Which adapter ran — matches CategorySourceConfig.source values
    source_adapter = models.CharField(max_length=50)

    # Which category this run served — FK so we can filter by category in admin
    category = models.ForeignKey(
        "categories.Category",
        on_delete=models.CASCADE,
        related_name="ingestion_runs",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_RUNNING,
    )

    # How many TrendItems were written in this run
    items_fetched = models.PositiveIntegerField(default=0)

    # Null on success, populated with exception string on failure.
    # TextField not CharField — stack traces can be long.
    error_message = models.TextField(null=True, blank=True)

    started_at = models.DateTimeField(auto_now_add=True)
    # Null until the run finishes (success or failure)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "ingestion_run"
        verbose_name = "ingestion run"
        verbose_name_plural = "ingestion runs"
        ordering = ["-started_at"]
        indexes = [
            # Fast lookup for "most recent successful run per category" query
            models.Index(fields=["category", "source_adapter", "-started_at"]),
            models.Index(fields=["status", "-started_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.category.name} / {self.source_adapter} — {self.status} @ {self.started_at:%Y-%m-%d %H:%M}"

    @property
    def duration_seconds(self) -> float | None:
        """How long the run took. None if still running."""
        if self.completed_at is None:
            return None
        return (self.completed_at - self.started_at).total_seconds()
