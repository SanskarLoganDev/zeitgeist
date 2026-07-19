"""
backend/apps/accounts/views.py
────────────────────────────────
Purpose : Handles simple session-based authentication for the application.

          GET /api/v1/auth/csrf/
            - Sets a CSRF cookie and returns the current CSRF token

          POST /api/v1/auth/register/
            - Creates an email/password account and emails a verification OTP

          POST /api/v1/auth/verify-email/
            - Verifies the emailed OTP and starts a Django session

          POST /api/v1/auth/resend-verification/
            - Resends a verification OTP for an unverified account

          POST /api/v1/auth/request-password-reset/
            - Emails a password reset OTP when the account exists

          POST /api/v1/auth/reset-password/
            - Verifies a password reset OTP and updates the password

          POST /api/v1/auth/login/
            - Authenticates email/password credentials and starts a Django session

          POST /api/v1/auth/logout/
            - Clears the Django session

          GET /api/v1/auth/me/
            - Returns the current authenticated user's profile
            - Called by Next.js on every page load to restore auth state

Used by : apps/accounts/urls.py — routes requests to these views
          Next.js frontend       — calls these endpoints for login/logout/session restore

Phase    : 1 — Week 3
"""
from __future__ import annotations

import logging

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.http import HttpRequest
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.email_verification import (
    EmailVerificationError,
    maybe_resend_registration_otp,
    maybe_send_password_reset_otp,
    reset_password_with_otp,
    send_registration_otp,
    verify_registration_otp,
)
from apps.accounts.models import User
from apps.accounts.rate_limits import AuthRateLimitError, enforce_auth_rate_limit
from apps.accounts.serializers import (
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    ResendVerificationSerializer,
    UserSerializer,
    VerifyEmailSerializer,
)

logger = logging.getLogger(__name__)


def _auth_payload(request: HttpRequest | Request) -> dict[str, object]:
    user = request.user
    if not user.is_authenticated:
        return {
            "authenticated": False,
            "user": None,
        }

    return {
        "authenticated": True,
        "user": UserSerializer(user).data,
    }


def _user_auth_payload(user: User) -> dict[str, object]:
    return {
        "authenticated": True,
        "user": UserSerializer(user).data,
    }


def _verification_required_payload(email: str) -> dict[str, object]:
    return {
        "authenticated": False,
        "user": None,
        "verification_required": True,
        "email": email,
        "resend_cooldown_seconds": settings.EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS,
        "detail": "Check your email for the verification code.",
    }


def _auth_config_payload() -> dict[str, object]:
    return {
        "email_verification": {
            "resend_cooldown_seconds": settings.EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS,
        }
    }


def _rate_limited_response() -> Response:
    return Response(
        {"detail": "Too many attempts. Please wait a minute and try again."},
        status=status.HTTP_429_TOO_MANY_REQUESTS,
    )


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CSRFTokenView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        return Response({"csrfToken": get_token(request)})


class AuthConfigView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        return Response(_auth_config_payload())


@method_decorator(csrf_protect, name="dispatch")
class RegisterView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        try:
            enforce_auth_rate_limit(
                request,
                scope="register",
                email=str(request.data.get("email", "")),
            )
        except AuthRateLimitError:
            return _rate_limited_response()

        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        try:
            send_registration_otp(user)
        except Exception:
            logger.exception("Registration verification email failed for user_id=%s", user.id)
            user.delete()
            return Response(
                {"detail": "Could not send verification email. Please try again later."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(
            _verification_required_payload(user.email),
            status=status.HTTP_201_CREATED,
        )


@method_decorator(csrf_protect, name="dispatch")
class VerifyEmailView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        try:
            enforce_auth_rate_limit(
                request,
                scope="verify-email",
                email=str(request.data.get("email", "")),
            )
        except AuthRateLimitError:
            return _rate_limited_response()

        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = verify_registration_otp(
                email=serializer.validated_data["email"],
                code=serializer.validated_data["code"],
            )
        except EmailVerificationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        login(request._request, user)
        return Response(_user_auth_payload(user))


@method_decorator(csrf_protect, name="dispatch")
class ResendVerificationView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        try:
            enforce_auth_rate_limit(
                request,
                scope="resend-verification",
                email=str(request.data.get("email", "")),
            )
        except AuthRateLimitError:
            return _rate_limited_response()

        serializer = ResendVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            maybe_resend_registration_otp(serializer.validated_data["email"])
        except EmailVerificationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "detail": "If that email needs verification, a new code has been sent.",
                "resend_cooldown_seconds": settings.EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS,
            }
        )


@method_decorator(csrf_protect, name="dispatch")
class RequestPasswordResetView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        try:
            enforce_auth_rate_limit(
                request,
                scope="request-password-reset",
                email=str(request.data.get("email", "")),
            )
        except AuthRateLimitError:
            return _rate_limited_response()

        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            maybe_send_password_reset_otp(serializer.validated_data["email"])
        except EmailVerificationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception(
                "Password reset email failed for email=%s",
                serializer.validated_data["email"],
            )
            return Response(
                {"detail": "Could not send password reset email. Please try again later."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {
                "detail": "If that email is registered, a password reset code has been sent.",
                "resend_cooldown_seconds": settings.EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS,
            }
        )


@method_decorator(csrf_protect, name="dispatch")
class ResetPasswordView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        try:
            enforce_auth_rate_limit(
                request,
                scope="reset-password",
                email=str(request.data.get("email", "")),
            )
        except AuthRateLimitError:
            return _rate_limited_response()

        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            reset_password_with_otp(
                email=serializer.validated_data["email"],
                code=serializer.validated_data["code"],
                new_password=serializer.validated_data["new_password"],
            )
        except EmailVerificationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"detail": "Your password has been updated. You can sign in now."})


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        try:
            enforce_auth_rate_limit(
                request,
                scope="login",
                email=str(request.data.get("email", "")),
            )
        except AuthRateLimitError:
            return _rate_limited_response()

        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]
        user = authenticate(request._request, username=email, password=password)
        if user is None:
            return Response(
                {"detail": "Invalid email or password."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not user.is_email_verified:
            return Response(
                _verification_required_payload(user.email),
                status=status.HTTP_403_FORBIDDEN,
            )

        login(request._request, user)
        return Response(_user_auth_payload(user))


@method_decorator(csrf_protect, name="dispatch")
class LogoutView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        logout(request._request)
        return Response({"authenticated": False, "user": None})


class CurrentUserView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        return Response(_auth_payload(request))
