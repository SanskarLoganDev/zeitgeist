from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.test import Client


def _csrf_token(client: Client) -> str:
    response = client.get("/api/v1/auth/csrf/")
    assert response.status_code == 200
    token = response.json()["csrfToken"]
    assert isinstance(token, str)
    return token


@pytest.mark.django_db
def test_register_creates_user_and_session() -> None:
    client = Client(enforce_csrf_checks=True)
    csrf_token = _csrf_token(client)

    response = client.post(
        "/api/v1/auth/register/",
        data={"email": "person@example.com", "password": "strong-password-123"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 201
    assert response.json()["authenticated"] is True
    assert response.json()["user"]["email"] == "person@example.com"
    assert get_user_model().objects.filter(email="person@example.com").exists()


@pytest.mark.django_db
def test_login_rejects_bad_password() -> None:
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
        data={"email": "person@example.com", "password": "wrong-password"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid email or password."


@pytest.mark.django_db
def test_me_returns_authenticated_user_after_login() -> None:
    user_model = get_user_model()
    user_model.objects.create_user(
        username="person@example.com",
        email="person@example.com",
        password="correct-password-123",
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
