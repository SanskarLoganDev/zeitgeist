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

# Phase 1 Week 2 — uncomment as models are implemented:
# from django.contrib import admin
# from .models import Category, SubredditConfig, CategorySourceConfig, UserCategoryPreference
# admin.site.register(Category)
# admin.site.register(SubredditConfig)
# admin.site.register(CategorySourceConfig)
