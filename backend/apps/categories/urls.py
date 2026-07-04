"""
backend/apps/categories/urls.py
─────────────────────────────────
Purpose : URL routes for the categories app. Mounted at /api/v1/ by config/urls.py.

          Routes:
            GET   /api/v1/categories/                   → CategoryListView        (Phase 1 Week 3)
            PATCH /api/v1/categories/preferences/       → PreferencesView         (Phase 2)
            GET   /api/v1/categories/{slug}/            → CategoryDetailView      (Phase 2)
            GET   /api/v1/categories/{slug}/trends/     → CategoryTrendsView      (Phase 2)
            GET   /api/v1/categories/{slug}/items/      → CategoryItemsView       (Phase 2)

Used by : config/urls.py — includes this file at the /api/v1/ prefix
          Next.js frontend — calls these endpoints

Phase    : 1 Week 3 (categories/ list), Phase 2 (all others)
"""
from django.urls import URLPattern, URLResolver, path

from apps.categories.views import CategoryListView, PreferencesView

urlpatterns: list[URLPattern | URLResolver] = [
    path("categories/", CategoryListView.as_view(), name="category-list"),
    path("categories/preferences/", PreferencesView.as_view(), name="category-preferences"),

    # Phase 2:
    # path("categories/<slug:slug>/",         CategoryDetailView.as_view(),  name="category-detail"),
    # path("categories/<slug:slug>/trends/",  CategoryTrendsView.as_view(),  name="category-trends"),
    # path("categories/<slug:slug>/items/",   CategoryItemsView.as_view(),   name="category-items"),
]
