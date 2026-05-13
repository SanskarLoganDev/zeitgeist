"""
backend/apps/trends/urls.py
─────────────────────────────
Purpose : URL routes for the trends app. Mounted at /api/v1/ by config/urls.py.

          Routes:
            GET  /api/v1/dashboard/                    → DashboardView        (Phase 1)
            GET  /api/v1/admin/ingestion/runs/         → IngestionRunListView (Phase 1)
            POST /api/v1/admin/ingestion/trigger/      → IngestionTriggerView (Phase 1)

Used by : config/urls.py — includes this file at the /api/v1/ prefix

Phase    : 1 Week 2 (admin views), Phase 1 Week 3 (dashboard)
"""
from django.urls import path

urlpatterns = [
    # Phase 1 Week 3:
    # path("dashboard/", DashboardView.as_view(), name="dashboard"),

    # Phase 1 Week 2:
    # path("admin/ingestion/runs/",    IngestionRunListView.as_view(),  name="ingestion-runs"),
    # path("admin/ingestion/trigger/", IngestionTriggerView.as_view(),  name="ingestion-trigger"),
]
