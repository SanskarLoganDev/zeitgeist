"""
backend/tests/test_health.py
──────────────────────────────
Purpose : Tests the /api/v1/health/ endpoint.
          This is the first and simplest test in the project.
          If this test passes, it confirms:
            - Django is correctly installed and importable
            - config/urls.py is wired correctly
            - The test database connection works
            - pytest-django is configured correctly in pyproject.toml

          This test is also what the GitHub Actions CD pipeline runs as a
          smoke test after every deployment — if the health endpoint returns
          anything other than 200, the deployment is flagged as failed.

Used by : pytest — run via `pytest` in the backend/ directory
          GitHub Actions ci.yml — part of the test suite on every push
          GitHub Actions cd.yml — smoke test hits the live URL after deploy
          (the CD smoke test hits the real URL, this test hits Django's test client)

Phase    : 1 — Week 1 (this test should pass before any other code is written)
"""
import pytest
from django.test import Client


@pytest.mark.django_db
def test_health_endpoint_returns_200():
    """Health check returns 200 OK."""
    client = Client()
    response = client.get("/api/v1/health/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_health_endpoint_returns_ok_status():
    """Health check response body contains status: ok."""
    client = Client()
    response = client.get("/api/v1/health/")
    assert response.json() == {"status": "ok"}
