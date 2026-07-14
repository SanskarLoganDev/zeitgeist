"""
Fetch popular recent/upcoming games using the RAWG games API.

RAWG does not provide a direct "trending" endpoint. This adapter uses a rolling
release-date window and sorts by user library adds, which is the clearest
available proxy for current gaming interest.
"""
from __future__ import annotations

import os
from datetime import timedelta
from typing import Any, NotRequired, TypedDict, cast

import requests
from django.utils import timezone

from apps.categories.models import Category
from apps.ingestion.adapters.base import BaseSourceAdapter, NormalizedTrendItem


class RawgGame(TypedDict):
    id: int
    slug: str
    name: str
    added: NotRequired[int]
    ratings_count: NotRequired[int]
    released: NotRequired[str | None]
    background_image: NotRequired[str | None]


class RawgAdapter(BaseSourceAdapter[RawgGame]):
    source_name = "rawg"
    games_url = "https://api.rawg.io/api/games"
    rawg_game_base_url = "https://rawg.io/games"
    days_back = 365
    days_forward = 90
    request_timeout_seconds = 10

    def __init__(
        self,
        session: requests.Session | None = None,
        api_key: str | None = None,
    ) -> None:
        self.session = session or requests.Session()
        self.api_key = api_key if api_key is not None else os.environ.get("RAWG_API_KEY")

    @classmethod
    def get_source_name(cls) -> str:
        return cls.source_name

    def fetch(self, category: Category, *, limit: int = 50) -> list[RawgGame]:
        if not self.api_key:
            raise RuntimeError("RAWG_API_KEY is required for RAWG ingestion")

        today = timezone.localdate()
        start_date = today - timedelta(days=self.days_back)
        end_date = today + timedelta(days=self.days_forward)

        params: dict[str, str | int] = {
            "key": self.api_key,
            "dates": f"{start_date.isoformat()},{end_date.isoformat()}",
            "ordering": "-added",
            "page_size": limit,
        }

        response = self.session.get(
            self.games_url,
            params=params,
            timeout=self.request_timeout_seconds,
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        payload = cast(object, response.json())

        if not isinstance(payload, dict):
            raise ValueError("RAWG games response was not an object")

        raw_results = payload.get("results")
        if not isinstance(raw_results, list):
            raise ValueError("RAWG games response did not include a results list")

        games: list[RawgGame] = []
        for item in raw_results:
            if not isinstance(item, dict):
                continue
            game = self._parse_game(cast(dict[str, Any], item))
            if game is not None:
                games.append(game)

        return games[:limit]

    def normalise(
        self,
        raw_item: RawgGame,
        category: Category,
        *,
        rank: int,
    ) -> NormalizedTrendItem:
        score = raw_item.get("added")
        score_label = "adds"
        if score is None:
            score = raw_item.get("ratings_count", 0)
            score_label = "ratings"

        game_url = f"{self.rawg_game_base_url}/{raw_item['slug']}"
        return NormalizedTrendItem(
            title=raw_item["name"],
            url=game_url,
            external_url=game_url,
            score=score,
            score_label=score_label,
            rank=rank,
        )

    def _parse_game(self, raw_item: dict[str, Any]) -> RawgGame | None:
        game_id = raw_item.get("id")
        slug = raw_item.get("slug")
        name = raw_item.get("name")

        if not isinstance(game_id, int):
            return None
        if not isinstance(slug, str) or not slug.strip():
            return None
        if not isinstance(name, str) or not name.strip():
            return None

        game = RawgGame(
            id=game_id,
            slug=slug.strip(),
            name=name.strip(),
        )

        added = raw_item.get("added")
        if isinstance(added, int):
            game["added"] = added

        ratings_count = raw_item.get("ratings_count")
        if isinstance(ratings_count, int):
            game["ratings_count"] = ratings_count

        released = raw_item.get("released")
        if isinstance(released, str) and released.strip():
            game["released"] = released.strip()

        background_image = raw_item.get("background_image")
        if isinstance(background_image, str) and background_image.strip():
            game["background_image"] = background_image.strip()

        return game
