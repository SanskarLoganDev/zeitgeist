"""
backend/apps/accounts/views.py
────────────────────────────────
Purpose : Handles simple session-based authentication for the application.

          GET /api/v1/auth/csrf/
            - Sets a CSRF cookie and returns the current CSRF token

          POST /api/v1/auth/register/
            - Creates an email/password account and starts a Django session

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

from apps.accounts.models import User
from apps.accounts.serializers import LoginSerializer, RegisterSerializer, UserSerializer


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


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CSRFTokenView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        return Response({"csrfToken": get_token(request)})


@method_decorator(csrf_protect, name="dispatch")
class RegisterView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        login(request._request, user)
        return Response(_user_auth_payload(user), status=status.HTTP_201_CREATED)


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
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
