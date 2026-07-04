from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from apps.categories.models import Category, UserCategoryPreference


@pytest.fixture
def categories() -> list[Category]:
    return [
        Category.objects.create(name="Tech", slug="tech", is_active=True),
        Category.objects.create(name="News", slug="news", is_active=True),
        Category.objects.create(name="Hidden", slug="hidden", is_active=False),
    ]


def _csrf_token(client: Client) -> str:
    response = client.get("/api/v1/auth/csrf/")
    assert response.status_code == 200
    token = response.json()["csrfToken"]
    assert isinstance(token, str)
    return token


@pytest.mark.django_db
def test_anonymous_preferences_are_readable_but_not_saveable(categories: list[Category]) -> None:
    del categories
    client = Client(enforce_csrf_checks=True)
    csrf_token = _csrf_token(client)

    get_response = client.get("/api/v1/categories/preferences/")
    patch_response = client.patch(
        "/api/v1/categories/preferences/",
        data={"selected_slugs": ["tech"]},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert get_response.status_code == 200
    assert get_response.json() == {"can_save": False, "selected_slugs": []}
    assert patch_response.status_code == 401


@pytest.mark.django_db
def test_logged_in_user_can_save_and_restore_preferences(categories: list[Category]) -> None:
    del categories
    user = get_user_model().objects.create_user(
        username="person@example.com",
        email="person@example.com",
        password="correct-password-123",
    )
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    csrf_token = _csrf_token(client)

    patch_response = client.patch(
        "/api/v1/categories/preferences/",
        data={"selected_slugs": ["tech", "news"]},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    get_response = client.get("/api/v1/categories/preferences/")

    assert patch_response.status_code == 200
    assert patch_response.json() == {"can_save": True, "selected_slugs": ["tech", "news"]}
    assert get_response.status_code == 200
    assert get_response.json() == {"can_save": True, "selected_slugs": ["news", "tech"]}
    assert UserCategoryPreference.objects.filter(user=user).count() == 2


@pytest.mark.django_db
def test_preferences_reject_inactive_categories(categories: list[Category]) -> None:
    del categories
    user = get_user_model().objects.create_user(
        username="person@example.com",
        email="person@example.com",
        password="correct-password-123",
    )
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    csrf_token = _csrf_token(client)

    response = client.patch(
        "/api/v1/categories/preferences/",
        data={"selected_slugs": ["hidden"]},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 400
    assert UserCategoryPreference.objects.filter(user=user).count() == 0
