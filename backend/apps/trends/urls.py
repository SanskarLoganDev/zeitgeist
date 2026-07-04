"""
backend/apps/trends/urls.py
─────────────────────────────
Purpose : URL routes for the trends app. Mounted at /api/v1/ by config/urls.py.

          Routes:
            GET  /api/v1/dashboard/                    → DashboardView        (Phase 1 Week 3)
            GET  /api/v1/admin/ingestion/runs/         → IngestionRunListView (Phase 1 Week 2)
            POST /api/v1/admin/ingestion/trigger/      → IngestionTriggerView (Phase 1 Week 2)

Used by : config/urls.py — includes this file at the /api/v1/ prefix

Phase    : 1 Week 2 (admin views), Phase 1 Week 3 (dashboard)
"""
from django.urls import URLPattern, URLResolver, path

from apps.trends.views import CategoryTrendsView, DashboardView

urlpatterns: list[URLPattern | URLResolver] = [
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("categories/<slug:slug>/trends/", CategoryTrendsView.as_view(), name="category-trends"),

    # Phase 1 Week 2:
    # path("admin/ingestion/runs/",    IngestionRunListView.as_view(),  name="ingestion-runs"),
    # path("admin/ingestion/trigger/", IngestionTriggerView.as_view(),  name="ingestion-trigger"),
]
