"""Fetch trending games from IGDB using PopScore popularity primitives."""
from __future__ import annotations

import os
import time
from typing import Any, ClassVar, NotRequired, TypedDict, cast

import requests

from apps.categories.models import Category
from apps.ingestion.adapters.base import BaseSourceAdapter, NormalizedTrendItem


class IgdbPopularityPrimitive(TypedDict):
    game_id: int
    popularity_type: int
    value: float


class IgdbGame(TypedDict):
    id: int
    name: str
    url: str
    slug: NotRequired[str]
    summary: NotRequired[str]
    cover_url: NotRequired[str]
    first_release_date: NotRequired[int]
    total_rating: NotRequired[float]
    total_rating_count: NotRequired[int]
    genres: NotRequired[list[str]]
    platforms: NotRequired[list[str]]


class IgdbGameTrend(TypedDict):
    game: IgdbGame
    trend_score: float
    component_values: dict[str, float]


class IgdbAdapter(BaseSourceAdapter[IgdbGameTrend]):
    source_name = "igdb"
    token_url = "https://id.twitch.tv/oauth2/token"
    api_base_url = "https://api.igdb.com/v4"
    igdb_game_base_url = "https://www.igdb.com/games"
    request_timeout_seconds = 10
    token_expiry_buffer_seconds = 60
    score_scale = 1_000_000

    popularity_types: ClassVar[dict[str, int]] = {
        "visits": 1,
        "want_to_play": 2,
        "playing": 3,
    }
    trend_weights: ClassVar[dict[str, float]] = {
        "visits": 0.50,
        "want_to_play": 0.30,
        "playing": 0.20,
    }

    def __init__(
        self,
        session: requests.Session | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        access_token: str | None = None,
    ) -> None:
        self.session = session or requests.Session()
        self.client_id = client_id if client_id is not None else os.environ.get("IGDB_CLIENT_ID")
        self.client_secret = (
            client_secret
            if client_secret is not None
            else os.environ.get("IGDB_CLIENT_SECRET")
        )
        self._access_token = access_token
        self._access_token_expires_at = float("inf") if access_token else 0.0

    @classmethod
    def get_source_name(cls) -> str:
        return cls.source_name

    def fetch(self, category: Category, *, limit: int = 50) -> list[IgdbGameTrend]:
        del category
        if not self.client_id:
            raise RuntimeError("IGDB_CLIENT_ID is required for IGDB ingestion")

        primitive_values = self._fetch_component_values(limit=limit)
        ranked_scores = self._ranked_scores(primitive_values)[:limit]
        games_by_id = self._fetch_games([game_id for game_id, _ in ranked_scores])

        trends: list[IgdbGameTrend] = []
        for game_id, trend_score in ranked_scores:
            game = games_by_id.get(game_id)
            if game is None:
                continue
            trends.append(
                IgdbGameTrend(
                    game=game,
                    trend_score=trend_score,
                    component_values=primitive_values[game_id],
                )
            )

        return trends[:limit]

    def normalise(
        self,
        raw_item: IgdbGameTrend,
        category: Category,
        *,
        rank: int,
    ) -> NormalizedTrendItem:
        del category
        game = raw_item["game"]

        return NormalizedTrendItem(
            title=game["name"],
            url=game["url"],
            external_url=game["url"],
            score=int(round(raw_item["trend_score"] * self.score_scale)),
            score_label="trend score",
            rank=rank,
            metadata={
                "game_id": game["id"],
                "trend_score": raw_item["trend_score"],
                "trend_weights": self.trend_weights,
                "component_values": raw_item["component_values"],
                "popularity_types": self.popularity_types,
                "first_release_date": game.get("first_release_date"),
                "total_rating": game.get("total_rating"),
                "total_rating_count": game.get("total_rating_count"),
                "genres": game.get("genres", []),
                "platforms": game.get("platforms", []),
                "cover_url": game.get("cover_url"),
                "summary": game.get("summary"),
            },
        )

    def _fetch_component_values(self, *, limit: int) -> dict[int, dict[str, float]]:
        values_by_game_id: dict[int, dict[str, float]] = {}

        for component, popularity_type in self.popularity_types.items():
            primitives = self._fetch_popularity_primitives(
                popularity_type=popularity_type,
                limit=limit,
            )
            for primitive in primitives:
                game_values = values_by_game_id.setdefault(primitive["game_id"], {})
                game_values[component] = primitive["value"]

        return values_by_game_id

    def _fetch_popularity_primitives(
        self,
        *,
        popularity_type: int,
        limit: int,
    ) -> list[IgdbPopularityPrimitive]:
        payload = self._post_igdb(
            "popularity_primitives",
            body=(
                "fields game_id,value,popularity_type; "
                f"where popularity_type = {popularity_type} & game_id != null; "
                "sort value desc; "
                f"limit {limit};"
            ),
        )
        if not isinstance(payload, list):
            raise ValueError("IGDB popularity_primitives response was not a list")

        primitives: list[IgdbPopularityPrimitive] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            primitive = self._parse_popularity_primitive(cast(dict[str, Any], item))
            if primitive is not None and primitive["popularity_type"] == popularity_type:
                primitives.append(primitive)

        return primitives[:limit]

    def _fetch_games(self, game_ids: list[int]) -> dict[int, IgdbGame]:
        if not game_ids:
            return {}

        id_list = ",".join(str(game_id) for game_id in game_ids)
        payload = self._post_igdb(
            "games",
            body=(
                "fields id,name,slug,url,summary,cover.url,first_release_date,"
                "total_rating,total_rating_count,genres.name,platforms.name; "
                f"where id = ({id_list}); "
                f"limit {len(game_ids)};"
            ),
        )
        if not isinstance(payload, list):
            raise ValueError("IGDB games response was not a list")

        games_by_id: dict[int, IgdbGame] = {}
        for item in payload:
            if not isinstance(item, dict):
                continue
            game = self._parse_game(cast(dict[str, Any], item))
            if game is not None:
                games_by_id[game["id"]] = game

        return games_by_id

    def _post_igdb(self, endpoint: str, *, body: str) -> object:
        response = self.session.post(
            f"{self.api_base_url}/{endpoint}",
            data=body,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self._get_access_token()}",
                "Client-ID": self.client_id or "",
            },
            timeout=self.request_timeout_seconds,
        )
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise RuntimeError(
                f"IGDB {endpoint} request failed with HTTP {response.status_code}: "
                f"{response.text[:300]}"
            ) from exc

        return cast(object, response.json())

    def _get_access_token(self) -> str:
        if self._access_token and time.time() < self._access_token_expires_at:
            return self._access_token
        if not self.client_secret:
            raise RuntimeError("IGDB_CLIENT_SECRET is required for IGDB ingestion")

        response = self.session.post(
            self.token_url,
            params={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "client_credentials",
            },
            timeout=self.request_timeout_seconds,
        )
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise RuntimeError(
                f"IGDB token request failed with HTTP {response.status_code}: "
                f"{response.text[:300]}"
            ) from exc

        payload = cast(object, response.json())
        if not isinstance(payload, dict):
            raise ValueError("IGDB token response was not an object")

        access_token = payload.get("access_token")
        expires_in = payload.get("expires_in")
        if not isinstance(access_token, str) or not access_token.strip():
            raise ValueError("IGDB token response did not include an access token")
        if not isinstance(expires_in, int):
            raise ValueError("IGDB token response did not include an expires_in value")

        self._access_token = access_token.strip()
        self._access_token_expires_at = (
            time.time() + expires_in - self.token_expiry_buffer_seconds
        )
        return self._access_token

    def _ranked_scores(
        self,
        primitive_values: dict[int, dict[str, float]],
    ) -> list[tuple[int, float]]:
        scores = [
            (
                game_id,
                sum(
                    values.get(component, 0.0) * weight
                    for component, weight in self.trend_weights.items()
                ),
            )
            for game_id, values in primitive_values.items()
        ]
        scores.sort(key=lambda item: item[1], reverse=True)
        return scores

    def _parse_popularity_primitive(
        self,
        raw_item: dict[str, Any],
    ) -> IgdbPopularityPrimitive | None:
        game_id = raw_item.get("game_id")
        popularity_type = raw_item.get("popularity_type")
        value = raw_item.get("value")

        if not isinstance(game_id, int):
            return None
        if not isinstance(popularity_type, int):
            return None
        if not isinstance(value, int | float):
            return None

        return IgdbPopularityPrimitive(
            game_id=game_id,
            popularity_type=popularity_type,
            value=float(value),
        )

    def _parse_game(self, raw_item: dict[str, Any]) -> IgdbGame | None:
        game_id = raw_item.get("id")
        name = raw_item.get("name")

        if not isinstance(game_id, int):
            return None
        if not isinstance(name, str) or not name.strip():
            return None

        slug = raw_item.get("slug")
        url = raw_item.get("url")
        game = IgdbGame(
            id=game_id,
            name=name.strip(),
            url=self._game_url(game_id=game_id, slug=slug, url=url),
        )

        if isinstance(slug, str) and slug.strip():
            game["slug"] = slug.strip()

        summary = raw_item.get("summary")
        if isinstance(summary, str) and summary.strip():
            game["summary"] = summary.strip()

        cover = raw_item.get("cover")
        cover_url = cover.get("url") if isinstance(cover, dict) else None
        if isinstance(cover_url, str) and cover_url.strip():
            game["cover_url"] = self._absolute_image_url(cover_url.strip())

        first_release_date = raw_item.get("first_release_date")
        if isinstance(first_release_date, int):
            game["first_release_date"] = first_release_date

        total_rating = raw_item.get("total_rating")
        if isinstance(total_rating, int | float):
            game["total_rating"] = float(total_rating)

        total_rating_count = raw_item.get("total_rating_count")
        if isinstance(total_rating_count, int):
            game["total_rating_count"] = total_rating_count

        genres = self._expanded_names(raw_item.get("genres"))
        if genres:
            game["genres"] = genres

        platforms = self._expanded_names(raw_item.get("platforms"))
        if platforms:
            game["platforms"] = platforms

        return game

    def _game_url(self, *, game_id: int, slug: object, url: object) -> str:
        if isinstance(url, str) and url.strip():
            return url.strip()
        if isinstance(slug, str) and slug.strip():
            return f"{self.igdb_game_base_url}/{slug.strip()}"
        return f"{self.igdb_game_base_url}/{game_id}"

    def _absolute_image_url(self, url: str) -> str:
        if url.startswith("//"):
            return f"https:{url}"
        return url

    def _expanded_names(self, value: object) -> list[str]:
        if not isinstance(value, list):
            return []

        names: list[str] = []
        for item in value:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            if isinstance(name, str) and name.strip():
                names.append(name.strip())

        return names
