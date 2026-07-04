"""
backend/apps/categories/views.py
─────────────────────────────────
Purpose : DRF API views for category listing and user preference management.

          Views:
            CategoryListView      GET /api/v1/categories/
              Returns all active categories with metadata (name, slug, source count,
              last_updated timestamp from the most recent IngestionRun).
              Used by Next.js to render the sidebar category list.

            CategoryDetailView    GET /api/v1/categories/{slug}/
              Returns top trending items for a category plus the Gemini AI summary
              (Phase 2). Checks Redis cache first; falls back to Postgres on miss.

            CategoryTrendsView    GET /api/v1/categories/{slug}/trends/
              Returns trend chart data — relative interest over a time window.
              Uses stored snapshots for recent windows, pytrends for historical.
              Phase 2 feature.

            CategoryItemsView     GET /api/v1/categories/{slug}/items/
              Paginated, filterable list of TrendItems. Supports ?source= and
              ?window= query params for source filter (FR-09) and time window (FR-07).
              Phase 2 feature.

            PreferencesView       PATCH /api/v1/categories/preferences/
              Updates the authenticated user's selected categories.
              Called by the inline preference editor on the dashboard (FR-03).

Used by : apps/categories/urls.py — routes requests to these views
          Next.js frontend        — dashboard, category pages, preference sidebar

Phase    : 1 Week 3 — CategoryListView
           Phase 2   — all other views
"""
from __future__ import annotations

from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.categories.models import Category, UserCategoryPreference
from apps.categories.serializers import CategoryPreferenceSerializer, CategorySerializer


class CategoryListView(ListAPIView[Category]):
    """
    Return active categories for the dashboard navigation.

    This endpoint reads only local database state. External APIs are called by
    ingestion jobs, not by request/response views.
    """

    serializer_class = CategorySerializer

    def get_queryset(self):  # type: ignore[no-untyped-def]
        return (
            Category.objects.filter(is_active=True)
            .prefetch_related("source_configs")
            .order_by("name")
        )


class PreferencesView(APIView):
    """
    Read or save the current user's category preferences.

    Anonymous users can read an empty preference state so the frontend can still
    render local-only controls. Saving requires a logged-in Django session.
    """

    authentication_classes = [SessionAuthentication]
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        if not request.user.is_authenticated:
            return Response({"can_save": False, "selected_slugs": []})

        selected_slugs = list(
            Category.objects.filter(user_preferences__user=request.user, is_active=True)
            .order_by("name")
            .values_list("slug", flat=True)
        )
        return Response({"can_save": True, "selected_slugs": selected_slugs})

    def patch(self, request: Request) -> Response:
        if not request.user.is_authenticated:
            return Response(
                {"detail": "Sign in to save category preferences."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        serializer = CategoryPreferenceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        selected_slugs = serializer.validated_data["selected_slugs"]
        selected_categories = Category.objects.filter(is_active=True, slug__in=selected_slugs)

        UserCategoryPreference.objects.filter(user=request.user).delete()
        UserCategoryPreference.objects.bulk_create(
            [
                UserCategoryPreference(user=request.user, category=category)
                for category in selected_categories
            ]
        )

        return Response({"can_save": True, "selected_slugs": selected_slugs})
