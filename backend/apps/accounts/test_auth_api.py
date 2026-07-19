from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import Client
from django.utils import timezone

from apps.accounts.email_verification import (
    EmailVerificationError,
    _hash_otp,
    send_registration_otp,
    verify_registration_otp,
)
from apps.accounts.models import EmailVerificationOTP, PasswordResetOTP


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
    assert "This code expires in 10 minutes." in mail.outbox[0].body


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
def test_login_rate_limit_returns_429(settings: Any) -> None:
    cache.clear()
    settings.AUTH_RATE_LIMIT_EMAIL_REQUESTS = 1
    settings.AUTH_RATE_LIMIT_IP_REQUESTS = 100
    user_model = get_user_model()
    user_model.objects.create_user(
        username="person@example.com",
        email="person@example.com",
        password="correct-password-123",
        email_verified_at=timezone.now(),
    )
    client = Client(enforce_csrf_checks=True)
    csrf_token = _csrf_token(client)

    first_response = client.post(
        "/api/v1/auth/login/",
        data={"email": "person@example.com", "password": "wrong-password"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    second_response = client.post(
        "/api/v1/auth/login/",
        data={"email": "person@example.com", "password": "wrong-password"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert first_response.status_code == 400
    assert second_response.status_code == 429


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


@pytest.mark.django_db
def test_password_reset_request_sends_code_for_verified_user(settings: Any) -> None:
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    user_model = get_user_model()
    user = user_model.objects.create_user(
        username="person@example.com",
        email="person@example.com",
        password="old-password-123",
        email_verified_at=timezone.now(),
    )
    client = Client(enforce_csrf_checks=True)
    csrf_token = _csrf_token(client)

    response = client.post(
        "/api/v1/auth/request-password-reset/",
        data={"email": "person@example.com"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 200
    assert response.json()["resend_cooldown_seconds"] == 60
    assert PasswordResetOTP.objects.filter(user=user).count() == 1
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["person@example.com"]
    assert "Your Zeitgeist password reset code" in mail.outbox[0].subject
    assert "This code expires in 10 minutes." in mail.outbox[0].body


@pytest.mark.django_db
def test_password_reset_request_does_not_reveal_unknown_email(settings: Any) -> None:
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    client = Client(enforce_csrf_checks=True)
    csrf_token = _csrf_token(client)

    response = client.post(
        "/api/v1/auth/request-password-reset/",
        data={"email": "missing@example.com"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 200
    assert "password reset code has been sent" in response.json()["detail"]
    assert PasswordResetOTP.objects.count() == 0
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_password_reset_updates_password() -> None:
    user_model = get_user_model()
    user = user_model.objects.create_user(
        username="person@example.com",
        email="person@example.com",
        password="old-password-123",
        email_verified_at=timezone.now(),
    )
    PasswordResetOTP.objects.create(
        user=user,
        sent_to_email=user.email,
        code_hash=_hash_otp("654321"),
        expires_at=timezone.now() + timedelta(minutes=10),
    )
    client = Client(enforce_csrf_checks=True)
    csrf_token = _csrf_token(client)

    reset_response = client.post(
        "/api/v1/auth/reset-password/",
        data={
            "email": "person@example.com",
            "code": "654321",
            "new_password": "new-password-456",
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    csrf_token = _csrf_token(client)
    login_response = client.post(
        "/api/v1/auth/login/",
        data={"email": "person@example.com", "password": "new-password-456"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert reset_response.status_code == 200
    assert login_response.status_code == 200
    assert login_response.json()["authenticated"] is True


@pytest.mark.django_db
def test_new_registration_otp_invalidates_existing_active_codes(settings: Any) -> None:
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    user_model = get_user_model()
    user = user_model.objects.create_user(
        username="person@example.com",
        email="person@example.com",
        password="correct-password-123",
    )
    old_otp = EmailVerificationOTP.objects.create(
        user=user,
        sent_to_email=user.email,
        code_hash=_hash_otp("111111"),
        expires_at=timezone.now() + timedelta(minutes=10),
    )

    send_registration_otp(user)

    old_otp.refresh_from_db()
    assert old_otp.consumed_at is not None
    assert EmailVerificationOTP.objects.filter(user=user, consumed_at__isnull=True).count() == 1
    with pytest.raises(EmailVerificationError):
        verify_registration_otp(email=user.email, code="111111")


@pytest.mark.django_db
def test_registration_otp_is_consumed_after_max_failed_attempts(settings: Any) -> None:
    settings.EMAIL_VERIFICATION_MAX_ATTEMPTS = 2
    user_model = get_user_model()
    user = user_model.objects.create_user(
        username="person@example.com",
        email="person@example.com",
        password="correct-password-123",
    )
    otp = EmailVerificationOTP.objects.create(
        user=user,
        sent_to_email=user.email,
        code_hash=_hash_otp("123456"),
        attempts=1,
        expires_at=timezone.now() + timedelta(minutes=10),
    )

    with pytest.raises(EmailVerificationError):
        verify_registration_otp(email=user.email, code="000000")

    otp.refresh_from_db()
    assert otp.attempts == 2
    assert otp.consumed_at is not None
    with pytest.raises(EmailVerificationError):
        verify_registration_otp(email=user.email, code="123456")
