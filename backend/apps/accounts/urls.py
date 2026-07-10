"""
backend/apps/accounts/urls.py
──────────────────────────────
Purpose : URL routes for the accounts app. Mounted at /api/v1/auth/ by config/urls.py.

          Auth uses email/password + Django session authentication (not Google OAuth).
          CSRF tokens are required for all mutating requests — frontend calls /csrf/
          first, then includes X-CSRFToken header on POST/PATCH requests.

          Routes:
            GET  /api/v1/auth/csrf/      → CSRFTokenView    (returns CSRF cookie + token)
            POST /api/v1/auth/register/  → RegisterView     (email + password signup)
            POST /api/v1/auth/login/     → LoginView        (email + password login)
            POST /api/v1/auth/logout/    → LogoutView       (clears Django session)
            GET  /api/v1/auth/me/        → CurrentUserView  (session restore on page load)

Used by : config/urls.py — includes this file at the /api/v1/auth/ prefix
          Next.js frontend — lib/auth.ts calls all of these endpoints

Phase    : 1 — Week 3 (complete)
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
