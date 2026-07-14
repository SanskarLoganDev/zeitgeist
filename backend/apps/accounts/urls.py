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
            POST /api/v1/auth/verify-email/        → VerifyEmailView
            POST /api/v1/auth/resend-verification/ → ResendVerificationView
            POST /api/v1/auth/request-password-reset/ → RequestPasswordResetView
            POST /api/v1/auth/reset-password/         → ResetPasswordView
            POST /api/v1/auth/login/               → LoginView
            POST /api/v1/auth/logout/              → LogoutView
            GET  /api/v1/auth/me/                  → CurrentUserView

Used by : config/urls.py — includes this file at the /api/v1/auth/ prefix
          Next.js frontend — lib/auth.ts calls all of these endpoints

Phase    : 1 — Week 3 (complete)
"""
from django.urls import URLPattern, URLResolver, path

from apps.accounts.views import (
    AuthConfigView,
    CSRFTokenView,
    CurrentUserView,
    LoginView,
    LogoutView,
    RegisterView,
    RequestPasswordResetView,
    ResendVerificationView,
    ResetPasswordView,
    VerifyEmailView,
)

urlpatterns: list[URLPattern | URLResolver] = [
    path("config/", AuthConfigView.as_view(), name="auth-config"),
    path("csrf/", CSRFTokenView.as_view(), name="auth-csrf"),
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("verify-email/", VerifyEmailView.as_view(), name="auth-verify-email"),
    path(
        "resend-verification/",
        ResendVerificationView.as_view(),
        name="auth-resend-verification",
    ),
    path(
        "request-password-reset/",
        RequestPasswordResetView.as_view(),
        name="auth-request-password-reset",
    ),
    path("reset-password/", ResetPasswordView.as_view(), name="auth-reset-password"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("me/", CurrentUserView.as_view(), name="auth-me"),
]
