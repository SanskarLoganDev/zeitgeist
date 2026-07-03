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
from django.contrib import admin

from .models import Category, CategorySourceConfig, SubredditConfig, UserCategoryPreference


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "parent", "icon", "is_active", "created_at")
    list_filter = ("is_active", "parent")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("name",)


@admin.register(SubredditConfig)
class SubredditConfigAdmin(admin.ModelAdmin):
    list_display = ("subreddit", "category", "is_active", "created_at")
    list_filter = ("is_active", "category")
    search_fields = ("subreddit", "category__name")
    autocomplete_fields = ("category",)
    ordering = ("category__name", "subreddit")


@admin.register(CategorySourceConfig)
class CategorySourceConfigAdmin(admin.ModelAdmin):
    list_display = ("category", "source", "is_active", "created_at")
    list_filter = ("source", "is_active", "category")
    search_fields = ("category__name", "source")
    autocomplete_fields = ("category",)
    ordering = ("category__name", "source")


@admin.register(UserCategoryPreference)
class UserCategoryPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "category", "created_at")
    list_filter = ("category", "created_at")
    search_fields = ("user__email", "user__username", "category__name")
    autocomplete_fields = ("user", "category")
