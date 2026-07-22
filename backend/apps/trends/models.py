"""
backend/apps/trends/models.py
───────────────────────────────
Purpose : Defines the core data models for trend storage and retrieval.

          Models:
            TrendSnapshot
              - One record per (category, ingestion run).
              - The anchor for a daily set of trend data.
              - This is what makes historical 7/30/90-day views possible (FR-07).
                Data accumulates from the very first ingestion run (FR-12).

            TrendItem
              - One record per trending post/paper/video/game within a snapshot.
              - source field identifies which adapter produced it.
              - score and score_label are normalised across sources.
              - ai_summary: reserved for future one-line summaries
              - sentiment: reserved for future Positive / Negative / Neutral badges

            CategoryAISummary
              - One Gemini-generated summary per category/ingestion batch.
              - Stored after ingestion so user requests never call Gemini.

Used by : apps/trends/views.py         — dashboard and category detail reads
          apps/ingestion/orchestrator.py — writes TrendSnapshot + TrendItem records
          apps/ai/client.py             — reads TrendItems to feed to Gemini (Phase 2)
          Django admin                  — staff can inspect ingestion output

Phase    : 1 — Week 2 (TrendSnapshot, TrendItem)
           Phase 2 — CategoryAISummary added to this file
"""
from django.db import models


class TrendSnapshot(models.Model):
    """
    One snapshot per (category, ingestion run). Acts as the anchor for a
    daily set of TrendItems from a specific source.

    Why a snapshot per source rather than per category?
    Each source is fetched independently by a separate adapter. A category
    can have multiple sources (e.g. Tech = Hacker News + DEV). Each source run
    creates its own snapshot. This means:
      - A failing source doesn't wipe the snapshot from a successful source
      - Historical views can be filtered by source (FR-09)
      - The stale indicator per source is accurate
    """

    category = models.ForeignKey(
        "categories.Category",
        on_delete=models.CASCADE,
        related_name="snapshots",
    )
    ingestion_run = models.ForeignKey(
        "ingestion.IngestionRun",
        on_delete=models.CASCADE,
        related_name="snapshots",
    )
    # Which source adapter produced this snapshot
    source = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "trends_snapshot"
        verbose_name = "trend snapshot"
        verbose_name_plural = "trend snapshots"
        ordering = ["-created_at"]
        indexes = [
            # Fast lookup for "latest snapshot per category per source"
            models.Index(fields=["category", "source", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.category.name} / {self.source} @ {self.created_at:%Y-%m-%d}"


class TrendItem(models.Model):
    """
    One trending item within a snapshot — an HN story,
    DEV article, NYT story, RAWG game, or Football-Data match.

    score and score_label are normalised across sources:
      HN        → points,              score_label="points"
      DEV       → reactions + comments, score_label="engagement"
      NYTimes   → rank-derived score,  score_label="most viewed"
      RAWG      → user library adds,   score_label="adds"
      Football  → match timestamp,     score_label="Full-time - 3-2"
      Cricket   → match timestamp,     score_label="India won by 4 wickets"

    external_url is the URL the item links to (the actual article/repo/video).
    url is the platform URL (e.g. the HN discussion URL).
    """

    SOURCE_HACKERNEWS = "hackernews"
    SOURCE_DEVTO = "devto"
    SOURCE_NYTIMES = "nytimes"
    SOURCE_RAWG = "rawg"
    SOURCE_FOOTBALL_DATA = "football_data"
    SOURCE_CRICKET_DATA = "cricket_data"

    SOURCE_CHOICES = [
        (SOURCE_HACKERNEWS, "Hacker News"),
        (SOURCE_DEVTO, "DEV"),
        (SOURCE_NYTIMES, "New York Times"),
        (SOURCE_RAWG, "RAWG"),
        (SOURCE_FOOTBALL_DATA, "Football-Data"),
        (SOURCE_CRICKET_DATA, "Cricket Data"),
    ]

    # Phase 3 sentiment choices
    SENTIMENT_POSITIVE = "positive"
    SENTIMENT_NEGATIVE = "negative"
    SENTIMENT_NEUTRAL = "neutral"

    SENTIMENT_CHOICES = [
        (SENTIMENT_POSITIVE, "Positive"),
        (SENTIMENT_NEGATIVE, "Negative"),
        (SENTIMENT_NEUTRAL, "Neutral"),
    ]

    snapshot = models.ForeignKey(
        TrendSnapshot,
        on_delete=models.CASCADE,
        related_name="items",
    )
    source = models.CharField(max_length=50, choices=SOURCE_CHOICES)

    title = models.TextField()
    # Platform URL — links to the post/story on the source platform.
    url = models.URLField(max_length=2000)
    # External URL — what the post links to (article, repo, paper).
    # Null for source-native posts without an external link (HN Ask/Show).
    external_url = models.URLField(max_length=2000, null=True, blank=True)

    # Normalised engagement or ordering score produced by the source adapter.
    score = models.BigIntegerField(default=0)
    # Human-readable label for the score — shown in the UI on trend cards
    score_label = models.CharField(max_length=50, default="score")
    metadata = models.JSONField(
        blank=True,
        default=dict,
        help_text="Optional source-specific display fields, e.g. football match details.",
    )

    # Rank within this snapshot — 1 = most trending
    rank = models.PositiveSmallIntegerField(default=1)

    # Reserved for future item-level summaries.
    ai_summary = models.TextField(null=True, blank=True)

    # Reserved for future sentiment classification.
    sentiment = models.CharField(
        max_length=20,
        choices=SENTIMENT_CHOICES,
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "trends_item"
        verbose_name = "trend item"
        verbose_name_plural = "trend items"
        ordering = ["snapshot", "rank"]
        indexes = [
            # Fast lookup for "top items in a snapshot"
            models.Index(fields=["snapshot", "rank"]),
            # Fast lookup for source filtering (FR-09)
            models.Index(fields=["snapshot", "source", "rank"]),
        ]

    def __str__(self) -> str:
        return f"[{self.source}] {self.title[:60]}"


class CategoryAISummary(models.Model):
    """
    One Gemini-generated category summary per ingestion batch/category.

    Summaries are generated by the ingestion job after source snapshots are
    written. They are served from Postgres by the dashboard/category APIs, never
    generated during a user request.
    """

    category = models.ForeignKey(
        "categories.Category",
        on_delete=models.CASCADE,
        related_name="ai_summaries",
    )
    summary_text = models.TextField()
    model_name = models.CharField(max_length=100)
    input_item_count = models.PositiveSmallIntegerField(default=0)
    metadata = models.JSONField(blank=True, default=dict)
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "trends_category_ai_summary"
        verbose_name = "category AI summary"
        verbose_name_plural = "category AI summaries"
        ordering = ["-generated_at"]
        indexes = [
            models.Index(fields=["category", "-generated_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.category.name} summary @ {self.generated_at:%Y-%m-%d %H:%M}"
