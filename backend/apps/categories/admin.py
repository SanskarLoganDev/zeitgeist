"""
backend/apps/categories/admin.py
──────────────────────────────────
Purpose : Registers category-related models in the Django admin panel.
          This is where admins add/edit categories, subreddits, and source
          adapter mappings — fulfilling FR-20 (no code deploy needed for
          new categories that use existing adapters).

          What admins can do here:
            - Add a new Category (e.g. "Sports") with a slug and icon
            - Add SubredditConfig rows to map subreddits to that category
            - Add CategorySourceConfig rows to enable Reddit/HN/YouTube for it
            - Toggle categories active/inactive without any deployment

Used by : Django admin panel — loaded automatically by Django at startup
          Staff users        — browse to /admin/ → Categories section

Phase    : 1 — Week 2 (register models as soon as they exist)
"""
from typing import TYPE_CHECKING, TypeAlias

from django.contrib import admin

from .models import Category, CategorySourceConfig, SubredditConfig, UserCategoryPreference

if TYPE_CHECKING:
    CategoryModelAdmin: TypeAlias = admin.ModelAdmin[Category]  # noqa: UP040
    SubredditConfigModelAdmin: TypeAlias = admin.ModelAdmin[SubredditConfig]  # noqa: UP040
    CategorySourceConfigModelAdmin: TypeAlias = admin.ModelAdmin[CategorySourceConfig]  # noqa: UP040
    UserCategoryPreferenceModelAdmin: TypeAlias = admin.ModelAdmin[UserCategoryPreference]  # noqa: UP040
else:
    CategoryModelAdmin = admin.ModelAdmin
    SubredditConfigModelAdmin = admin.ModelAdmin
    CategorySourceConfigModelAdmin = admin.ModelAdmin
    UserCategoryPreferenceModelAdmin = admin.ModelAdmin


@admin.register(Category)
class CategoryAdmin(CategoryModelAdmin):
    list_display = ("name", "slug", "parent", "icon", "is_active", "created_at")
    list_filter = ("is_active", "parent")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("name",)


@admin.register(SubredditConfig)
class SubredditConfigAdmin(SubredditConfigModelAdmin):
    list_display = ("subreddit", "category", "is_active", "created_at")
    list_filter = ("is_active", "category")
    search_fields = ("subreddit", "category__name")
    autocomplete_fields = ("category",)
    ordering = ("category__name", "subreddit")


@admin.register(CategorySourceConfig)
class CategorySourceConfigAdmin(CategorySourceConfigModelAdmin):
    list_display = ("category", "source", "is_active", "created_at")
    list_filter = ("source", "is_active", "category")
    search_fields = ("category__name", "source")
    autocomplete_fields = ("category",)
    ordering = ("category__name", "source")


@admin.register(UserCategoryPreference)
class UserCategoryPreferenceAdmin(UserCategoryPreferenceModelAdmin):
    list_display = ("user", "category", "created_at")
    list_filter = ("category", "created_at")
    search_fields = ("user__email", "user__username", "category__name")
    autocomplete_fields = ("user", "category")
