"""
backend/config/urls.py
──────────────────────
Purpose : The root URL configuration for the entire Django project.
          Every HTTP request that reaches the API server is routed here first.
          This file maps URL prefixes to the urls.py of each Django app.

          Current routes:
            /admin/              → Django admin panel (staff only)
            /api/v1/health/      → Lightweight health check (used by CI/CD smoke test + Cloud Run)
            /api/v1/auth/        → accounts app URLs (OAuth login, logout, me)
            /api/v1/             → categories app URLs (list, detail, preferences)
            /api/v1/             → trends app URLs (dashboard, ingestion admin)

Used by : config/wsgi.py — Django loads this file at startup via ROOT_URLCONF setting.
          Every inbound HTTP request is dispatched through this file.

NOT used by : run_job.py (the ingestion job never receives HTTP requests).
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse


def health(request):
    """
    Lightweight health check endpoint.
    Returns 200 {"status": "ok"} if Django is running and the DB connection is live.

    Called by:
      - GitHub Actions CD pipeline smoke test (after every deploy)
      - Cloud Run startup probe (to know when the container is ready for traffic)
      - Cloud Monitoring uptime check (Phase 3)
    """
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/health/", health),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.categories.urls")),
    path("api/v1/", include("apps.trends.urls")),
]
