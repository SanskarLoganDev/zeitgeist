from __future__ import annotations

from typing import Any

import pytest
import requests

from apps.categories.models import Category
from apps.ingestion.adapters.igdb import IgdbAdapter


class FakeResponse:
    def __init__(
        self,
        payload: object,
        *,
        status_code: int = 200,
        text: str = "",
    ) -> None:
        self.payload = payload
        self.status_code = status_code
        self.text = text

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError("request failed")

    def json(self) -> object:
        return self.payload


class FakeSession:
    def __init__(self, responses: dict[str, object]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def post(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append((url, kwargs))
        if url == IgdbAdapter.token_url:
            return FakeResponse({"access_token": "test-access-token", "expires_in": 3600})

        endpoint = url.rsplit("/", maxsplit=1)[-1]
        payload = self.responses[endpoint]
        if isinstance(payload, FakeResponse):
            return payload
        return FakeResponse(payload)


def test_fetch_combines_popscore_components_and_hydrates_games() -> None:
    session = FakeSession(
        {
            "popularity_primitives": [
                {"game_id": 1, "popularity_type": 1, "value": 0.90},
                {"game_id": 2, "popularity_type": 1, "value": 0.50},
                {"game_id": 3, "popularity_type": 1, "value": 0.40},
                {"game_id": 1, "popularity_type": 2, "value": 0.10},
                {"game_id": 2, "popularity_type": 2, "value": 0.90},
                {"game_id": 1, "popularity_type": 3, "value": 0.10},
                {"game_id": 2, "popularity_type": 3, "value": 0.80},
            ],
            "games": [
                {
                    "id": 1,
                    "name": "Visit Heavy Game",
                    "slug": "visit-heavy-game",
                    "url": "https://www.igdb.com/games/visit-heavy-game",
                    "cover": {"url": "//images.igdb.com/igdb/image/upload/t_cover_big/game.jpg"},
                    "genres": [{"name": "Adventure"}],
                    "platforms": [{"name": "PC"}],
                    "first_release_date": 1_735_689_600,
                    "total_rating": 88.5,
                    "total_rating_count": 120,
                },
                {
                    "id": 2,
                    "name": "Balanced Game",
                    "slug": "balanced-game",
                    "url": "https://www.igdb.com/games/balanced-game",
                },
            ],
        }
    )
    adapter = IgdbAdapter(
        session=session, client_id="client-id", client_secret="client-secret"
    )

    items = adapter.fetch(Category(name="Gaming", slug="gaming"), limit=2)

    assert [item["game"]["id"] for item in items] == [2, 1]
    assert items[0]["trend_score"] == pytest.approx(0.68)
    assert items[0]["component_values"] == {
        "visits": 0.50,
        "want_to_play": 0.90,
        "playing": 0.80,
    }
    assert items[1]["trend_score"] == pytest.approx(0.50)
    assert items[1]["game"]["cover_url"] == (
        "https://images.igdb.com/igdb/image/upload/t_cover_big/game.jpg"
    )

    token_calls = [call for call in session.calls if call[0] == IgdbAdapter.token_url]
    assert len(token_calls) == 1
    assert token_calls[0][1]["params"] == {
        "client_id": "client-id",
        "client_secret": "client-secret",
        "grant_type": "client_credentials",
    }

    igdb_calls = [call for call in session.calls if call[0] != IgdbAdapter.token_url]
    assert [call[0] for call in igdb_calls] == [
        f"{IgdbAdapter.api_base_url}/popularity_primitives",
        f"{IgdbAdapter.api_base_url}/popularity_primitives",
        f"{IgdbAdapter.api_base_url}/popularity_primitives",
        f"{IgdbAdapter.api_base_url}/games",
    ]
    assert all(
        call[1]["headers"]["Authorization"] == "Bearer test-access-token"
        for call in igdb_calls
    )
    assert "where popularity_type = 1" in igdb_calls[0][1]["data"]
    assert "where popularity_type = 2" in igdb_calls[1][1]["data"]
    assert "where popularity_type = 3" in igdb_calls[2][1]["data"]


def test_normalise_uses_scaled_weighted_score_and_metadata() -> None:
    adapter = IgdbAdapter(access_token="token", client_id="client-id")

    item = adapter.normalise(
        {
            "game": {
                "id": 2,
                "name": "Balanced Game",
                "url": "https://www.igdb.com/games/balanced-game",
                "first_release_date": 1_735_689_600,
                "total_rating": 91.2,
                "genres": ["Role-playing"],
                "platforms": ["PC", "PlayStation 5"],
            },
            "trend_score": 0.68123,
            "component_values": {
                "visits": 0.50,
                "want_to_play": 0.90,
                "playing": 0.80615,
            },
        },
        Category(name="Gaming", slug="gaming"),
        rank=3,
    )

    assert item.title == "Balanced Game"
    assert item.url == "https://www.igdb.com/games/balanced-game"
    assert item.external_url == "https://www.igdb.com/games/balanced-game"
    assert item.score == 681_230
    assert item.score_label == "trend score"
    assert item.rank == 3
    assert item.metadata["trend_weights"] == {
        "visits": 0.50,
        "want_to_play": 0.30,
        "playing": 0.20,
    }
    assert item.metadata["component_values"] == {
        "visits": 0.50,
        "want_to_play": 0.90,
        "playing": 0.80615,
    }


def test_fetch_requires_client_id() -> None:
    adapter = IgdbAdapter(session=FakeSession({}), client_id="", client_secret="secret")

    with pytest.raises(RuntimeError, match="IGDB_CLIENT_ID is required"):
        adapter.fetch(Category(name="Gaming", slug="gaming"))


def test_fetch_requires_client_secret_when_token_is_not_prefetched() -> None:
    adapter = IgdbAdapter(session=FakeSession({}), client_id="client-id", client_secret="")

    with pytest.raises(RuntimeError, match="IGDB_CLIENT_SECRET is required"):
        adapter.fetch(Category(name="Gaming", slug="gaming"))


def test_fetch_raises_readable_api_error() -> None:
    adapter = IgdbAdapter(
        session=FakeSession(
            {
                "popularity_primitives": FakeResponse(
                    {"message": "rate limited"},
                    status_code=429,
                    text="rate limited",
                )
            }
        ),
        client_id="client-id",
        client_secret="client-secret",
    )

    with pytest.raises(RuntimeError, match="IGDB popularity_primitives request failed"):
        adapter.fetch(Category(name="Gaming", slug="gaming"))
