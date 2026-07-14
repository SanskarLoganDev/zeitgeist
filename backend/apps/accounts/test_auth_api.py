from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import Client
from django.utils import timezone

from apps.accounts.email_verification import _hash_otp
from apps.accounts.models import EmailVerificationOTP


def _csrf_token(client: Client) -> str:
    response = client.get("/api/v1/auth/csrf/")
    assert response.status_code == 200
    token = response.json()["csrfToken"]
    assert isinstance(token, str)
    return token


@pytest.mark.django_db
def test_register_creates_user_and_sends_verification_code(settings: Any) -> None:
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.DEFAULT_FROM_EMAIL = "Zeitgeist <test@example.com>"
    client = Client(enforce_csrf_checks=True)
    csrf_token = _csrf_token(client)

    response = client.post(
        "/api/v1/auth/register/",
        data={"email": "person@example.com", "password": "strong-password-123"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 201
    assert response.json()["authenticated"] is False
    assert response.json()["verification_required"] is True
    assert response.json()["resend_cooldown_seconds"] == 60
    user = get_user_model().objects.get(email="person@example.com")
    assert user.email_verified_at is None
    assert EmailVerificationOTP.objects.filter(user=user).count() == 1
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["person@example.com"]
    assert "Your Zeitgeist verification code" in mail.outbox[0].subject


@pytest.mark.django_db
def test_verify_email_marks_user_verified_and_starts_session() -> None:
    user_model = get_user_model()
    user = user_model.objects.create_user(
        username="person@example.com",
        email="person@example.com",
        password="correct-password-123",
    )
    EmailVerificationOTP.objects.create(
        user=user,
        sent_to_email=user.email,
        code_hash=_hash_otp("123456"),
        expires_at=timezone.now() + timedelta(minutes=10),
    )
    client = Client(enforce_csrf_checks=True)
    csrf_token = _csrf_token(client)

    response = client.post(
        "/api/v1/auth/verify-email/",
        data={"email": "person@example.com", "code": "123456"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    me_response = client.get("/api/v1/auth/me/")

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.email_verified_at is not None
    assert me_response.json()["authenticated"] is True
    assert me_response.json()["user"]["email"] == "person@example.com"


@pytest.mark.django_db
def test_login_rejects_bad_password() -> None:
    user_model = get_user_model()
    user_model.objects.create_user(
        username="person@example.com",
        email="person@example.com",
        password="correct-password-123",
        email_verified_at=timezone.now(),
    )
    client = Client(enforce_csrf_checks=True)
    csrf_token = _csrf_token(client)

    response = client.post(
        "/api/v1/auth/login/",
        data={"email": "person@example.com", "password": "wrong-password"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid email or password."


@pytest.mark.django_db
def test_login_rejects_unverified_email() -> None:
    user_model = get_user_model()
    user_model.objects.create_user(
        username="person@example.com",
        email="person@example.com",
        password="correct-password-123",
    )
    client = Client(enforce_csrf_checks=True)
    csrf_token = _csrf_token(client)

    response = client.post(
        "/api/v1/auth/login/",
        data={"email": "person@example.com", "password": "correct-password-123"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 403
    assert response.json()["verification_required"] is True
    assert response.json()["resend_cooldown_seconds"] == 60


@pytest.mark.django_db
def test_auth_config_returns_resend_cooldown() -> None:
    client = Client()

    response = client.get("/api/v1/auth/config/")

    assert response.status_code == 200
    assert response.json()["email_verification"]["resend_cooldown_seconds"] == 60


@pytest.mark.django_db
def test_me_returns_authenticated_user_after_login() -> None:
    user_model = get_user_model()
    user_model.objects.create_user(
        username="person@example.com",
        email="person@example.com",
        password="correct-password-123",
        email_verified_at=timezone.now(),
    )
    client = Client(enforce_csrf_checks=True)
    csrf_token = _csrf_token(client)

    login_response = client.post(
        "/api/v1/auth/login/",
        data={"email": "person@example.com", "password": "correct-password-123"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    me_response = client.get("/api/v1/auth/me/")

    assert login_response.status_code == 200
    assert me_response.status_code == 200
    assert me_response.json()["authenticated"] is True
    assert me_response.json()["user"]["email"] == "person@example.com"


@pytest.mark.django_db
def test_logout_clears_session() -> None:
    user_model = get_user_model()
    user_model.objects.create_user(
        username="person@example.com",
        email="person@example.com",
        password="correct-password-123",
        email_verified_at=timezone.now(),
    )
    client = Client(enforce_csrf_checks=True)
    csrf_token = _csrf_token(client)
    client.post(
        "/api/v1/auth/login/",
        data={"email": "person@example.com", "password": "correct-password-123"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    csrf_token = _csrf_token(client)

    response = client.post(
        "/api/v1/auth/logout/",
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    me_response = client.get("/api/v1/auth/me/")

    assert response.status_code == 200
    assert me_response.json()["authenticated"] is False
