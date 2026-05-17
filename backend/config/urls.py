"""
backend/config/urls.py
──────────────────────
Purpose : The root URL configuration for the entire Django project.
          Every HTTP request that reaches the API server is routed here first.
          This file maps URL prefixes to the urls.py of each Django app.

          Current routes:
            /admin/              → Django admin panel (staff only)
            /api/v1/health/      → Lightweight health check (CI/CD smoke test + Cloud Run probe)
            /api/v1/auth/        → accounts app URLs (OAuth login, logout, me)
            /api/v1/             → categories app URLs (list, detail, preferences)
            /api/v1/             → trends app URLs (dashboard, ingestion admin)

Used by : config/wsgi.py — Django loads this via ROOT_URLCONF setting.
          Every inbound HTTP request is dispatched through this file.

NOT used by : run_job.py (the ingestion job never receives HTTP requests).
"""
from django.contrib import admin
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.urls import include, path


def health(request: HttpRequest) -> HttpResponse:
    """
    Lightweight health check endpoint.
    Returns 200 {"status": "ok"} if Django is running.

    Called by:
      - GitHub Actions CD pipeline smoke test after every deploy
      - Cloud Run startup probe to know when container is ready
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
