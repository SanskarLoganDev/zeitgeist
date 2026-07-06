"""
backend/apps/categories/models.py
───────────────────────────────────
Purpose : Defines the data models for categories and the mapping between
          categories and source adapters.

          Models:
            Category
              - The top-level interest areas: Tech, Gaming, News, etc.
              - Self-referential FK (parent) enables subcategories — the FK
                exists from day 1 so migrations don't need retrofitting, but
                the subcategory UI is not activated until Phase 2.
              - slug field used in all API URLs: /api/v1/categories/gaming/

            CategorySourceConfig
              - Maps a Category to a source adapter (hackernews, devto, youtube…)
              - Controls which adapters run for which category during ingestion.
              - Example: { category: Tech, source: "hackernews", active: True }

            UserCategoryPreference
              - Join table: which categories a user has selected for their dashboard.
              - Created during onboarding (Phase 3) or inline edit (Phase 2, FR-03).
              - Added here as a stub so the FK to Category exists from day 1.

Used by : apps/categories/views.py      — CategoryListView, PreferencesView
          apps/ingestion/orchestrator.py — reads CategorySourceConfig to know
                                           which adapters to run per category
          apps/trends/views.py           — reads UserCategoryPreference to filter dashboard
          Django admin                   — admins edit CategorySourceConfig

Phase    : 1 — Week 2
"""
from django.conf import settings
from django.db import models


class Category(models.Model):
    """
    A top-level interest area — Tech, Gaming, News, Finance, Health, Space,
    Research, TV/Movies, Food.

    self-referential FK on `parent` enables subcategories (Phase 2):
      e.g. Category(name="AI/ML", parent=Category(name="Tech"))
    The FK exists from day 1 so no painful migration later. Subcategory
    UI and API filtering are not activated until Phase 2.
    """

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    # Self-referential FK — null for top-level categories, set for subcategories
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="children",
    )
    icon = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Emoji or icon name for the UI — e.g. '🎮' or 'gaming'",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Inactive categories are hidden from the dashboard and skipped during ingestion",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "categories_category"
        verbose_name = "category"
        verbose_name_plural = "categories"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class CategorySourceConfig(models.Model):
    """
    Maps a Category to a source adapter. Controls which adapters the orchestrator
    runs for each category during ingestion.

    Source choices are kept as string constants here — not a FK to a Source
    model — because the set of sources is fixed by the adapter codebase, not
    by admin configuration. Adding a new source type always requires a code
    deploy regardless (new adapter class). Only new categories using existing
    sources require admin config only (FR-20).
    """

    SOURCE_HACKERNEWS = "hackernews"
    SOURCE_DEVTO = "devto"
    SOURCE_NYTIMES = "nytimes"
    SOURCE_RAWG = "rawg"
    SOURCE_YOUTUBE = "youtube"        # Phase 2
    SOURCE_ARXIV = "arxiv"            # Phase 2
    SOURCE_PUBMED = "pubmed"          # Phase 2
    SOURCE_TMDB = "tmdb"              # Phase 2
    SOURCE_NASA = "nasa"              # Phase 2

    SOURCE_CHOICES = [
        (SOURCE_HACKERNEWS, "Hacker News"),
        (SOURCE_DEVTO, "DEV"),
        (SOURCE_NYTIMES, "New York Times"),
        (SOURCE_RAWG, "RAWG"),
        (SOURCE_YOUTUBE, "YouTube"),
        (SOURCE_ARXIV, "arXiv"),
        (SOURCE_PUBMED, "PubMed"),
        (SOURCE_TMDB, "TMDB"),
        (SOURCE_NASA, "NASA"),
    ]

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="source_configs",
    )
    source = models.CharField(max_length=50, choices=SOURCE_CHOICES)
    is_active = models.BooleanField(
        default=True,
        help_text="Inactive sources are skipped during ingestion for this category",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "categories_source_config"
        verbose_name = "category source config"
        verbose_name_plural = "category source configs"
        unique_together = [("category", "source")]
        ordering = ["category__name", "source"]

    def __str__(self) -> str:
        return f"{self.category.name} ← {self.get_source_display()}"


class UserCategoryPreference(models.Model):
    """
    Join table between a User and the Categories they have selected.

    Stub for Phase 1 — the FK to Category is established here so no
    painful migrations later. The preference editing UI and the dashboard
    filter that reads this table are implemented in Phase 2 (FR-03) and
    Phase 3 (FR-02 onboarding).

    In Phase 1 the dashboard shows all active categories for all users.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="category_preferences",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="user_preferences",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "categories_user_preference"
        verbose_name = "user category preference"
        verbose_name_plural = "user category preferences"
        unique_together = [("user", "category")]

    def __str__(self) -> str:
        return f"{self.user} → {self.category.name}"
