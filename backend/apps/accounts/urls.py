"""
backend/apps/accounts/urls.py
──────────────────────────────
Purpose : URL routes for the accounts app. Mounted at /api/v1/auth/ by config/urls.py.

          Routes:
            POST /api/v1/auth/google/  → GoogleOAuthCallbackView  (login)
            POST /api/v1/auth/logout/  → LogoutView
            GET  /api/v1/auth/me/      → CurrentUserView          (session restore)

Used by : config/urls.py — includes this file at the /api/v1/auth/ prefix
          Next.js frontend — calls these endpoints

Phase    : 1 — Week 3
"""
from django.urls import path

urlpatterns = [
    # Phase 1 Week 3:
    # path("google/",  GoogleOAuthCallbackView.as_view(), name="auth-google"),
    # path("logout/",  LogoutView.as_view(),              name="auth-logout"),
    # path("me/",      CurrentUserView.as_view(),         name="auth-me"),
]
