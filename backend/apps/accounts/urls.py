"""
backend/apps/accounts/urls.py
──────────────────────────────
Purpose : URL routes for the accounts app. Mounted at /api/v1/auth/ by config/urls.py.

          Routes (all implemented in Phase 1 Week 3):
            POST /api/v1/auth/google/  → GoogleOAuthCallbackView  (login)
            POST /api/v1/auth/logout/  → LogoutView
            GET  /api/v1/auth/me/      → CurrentUserView          (session restore)

Used by : config/urls.py — includes this file at the /api/v1/auth/ prefix
          Next.js frontend — calls these endpoints

Phase    : 1 — Week 3
"""
from django.urls import URLPattern, URLResolver, path

from apps.accounts.views import CSRFTokenView, CurrentUserView, LoginView, LogoutView, RegisterView

urlpatterns: list[URLPattern | URLResolver] = [
    path("csrf/", CSRFTokenView.as_view(), name="auth-csrf"),
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("me/", CurrentUserView.as_view(), name="auth-me"),
]
