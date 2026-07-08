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
              - ai_summary (Phase 2): one-line Gemini-generated summary per item
              - sentiment (Phase 3): Positive / Negative / Neutral badge

            CategoryAISummary and CrossPlatformTopic are NOT added here.
            CategoryAISummary → Phase 2 Week 5 (when Gemini client is built)
            CrossPlatformTopic → Phase 3 (when embedding detection is built)

Used by : apps/trends/views.py         — dashboard and category detail reads
          apps/ingestion/orchestrator.py — writes TrendSnapshot + TrendItem records
          apps/ai/client.py             — reads TrendItems to feed to Gemini (Phase 2)
          Django admin                  — staff can inspect ingestion output

Phase    : 1 — Week 2 (TrendSnapshot, TrendItem)
           Phase 2 — CategoryAISummary added to this file
           Phase 3 — CrossPlatformTopic added to this file
"""
from django.db import models


class TrendSnapshot(models.Model):
    """
    One snapshot per (category, ingestion run). Acts as the anchor for a
    daily set of TrendItems from a specific source.

    Why a snapshot per source rather than per category?
    Each source is fetched independently by a separate adapter. A category
    can have multiple sources (e.g. Tech = HN + arXiv). Each source run
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
    DEV article, YouTube video, arXiv paper, etc.

    score and score_label are normalised across sources:
      HN        → points,              score_label="points"
      DEV       → reactions + comments, score_label="engagement"
      NYTimes   → rank-derived score,  score_label="most viewed"
      RAWG      → user library adds,   score_label="adds"
      Football  → match timestamp,     score_label="Full-time - 3-2"
      YouTube   → view count,          score_label="views"
      arXiv     → rank,                score_label="recent submissions"
      PubMed    → citations,           score_label="citations"
      TMDB      → popularity,          score_label="popularity"
      NASA      → rank,                score_label="featured"

    external_url is the URL the item links to (the actual article/repo/video).
    url is the platform URL (e.g. the HN discussion URL).
    """

    SOURCE_HACKERNEWS = "hackernews"
    SOURCE_DEVTO = "devto"
    SOURCE_NYTIMES = "nytimes"
    SOURCE_RAWG = "rawg"
    SOURCE_FOOTBALL_DATA = "football_data"
    SOURCE_YOUTUBE = "youtube"
    SOURCE_ARXIV = "arxiv"
    SOURCE_PUBMED = "pubmed"
    SOURCE_TMDB = "tmdb"
    SOURCE_NASA = "nasa"

    SOURCE_CHOICES = [
        (SOURCE_HACKERNEWS, "Hacker News"),
        (SOURCE_DEVTO, "DEV"),
        (SOURCE_NYTIMES, "New York Times"),
        (SOURCE_RAWG, "RAWG"),
        (SOURCE_FOOTBALL_DATA, "Football-Data"),
        (SOURCE_YOUTUBE, "YouTube"),
        (SOURCE_ARXIV, "arXiv"),
        (SOURCE_PUBMED, "PubMed"),
        (SOURCE_TMDB, "TMDB"),
        (SOURCE_NASA, "NASA"),
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

    # Normalised engagement score — points for HN, views for YouTube, etc.
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

    # Phase 2 — Gemini-generated one-line summary per item.
    # Null until Phase 2 ingestion job generates it.
    ai_summary = models.TextField(null=True, blank=True)

    # Phase 3 — Gemini sentiment classification.
    # Null until Phase 3 ingestion job generates it.
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
