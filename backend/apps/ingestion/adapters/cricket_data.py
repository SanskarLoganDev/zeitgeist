"""Fetch current and recent cricket matches using the Cricket Data API.

The Sports UI shows cricket like football: current matches plus recent results,
not a generic popularity feed. The adapter keeps completed/past matches from the
last 14 UTC days and caps the normalized feed at the orchestrator limit.
"""
from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from typing import Any, NotRequired, TypedDict, cast

import requests
from django.utils.dateparse import parse_date, parse_datetime

from apps.categories.models import Category
from apps.ingestion.adapters.base import BaseSourceAdapter, NormalizedTrendItem


class CricketDataScore(TypedDict, total=False):
    r: int
    w: int
    o: float | int | str
    inning: str


class CricketDataMatch(TypedDict):
    id: str
    name: str
    status: str
    matchType: NotRequired[str | None]
    venue: NotRequired[str | None]
    date: NotRequired[str | None]
    dateTimeGMT: NotRequired[str | None]
    teams: NotRequired[list[str]]
    score: NotRequired[list[CricketDataScore]]
    series_id: NotRequired[str | None]
    fantasyEnabled: NotRequired[bool]
    is_current: bool


class CricketDataAdapter(BaseSourceAdapter[CricketDataMatch]):
    source_name = "cricket_data"
    source_home_url = "https://cricketdata.org/"
    api_base_url = "https://api.cricapi.com/v1"
    page_size = 25
    max_current_pages = 2
    max_match_pages = 8
    lookback_days = 14
    current_match_score_bonus = 86_400
    request_timeout_seconds = 10

    def __init__(
        self,
        session: requests.Session | None = None,
        api_key: str | None = None,
    ) -> None:
        self.session = session or requests.Session()
        self.api_key = api_key if api_key is not None else os.environ.get("CRICKET_DATA_API_KEY")

    @classmethod
    def get_source_name(cls) -> str:
        return cls.source_name

    def fetch(self, category: Category, *, limit: int = 50) -> list[CricketDataMatch]:
        if not self.api_key:
            raise RuntimeError("CRICKET_DATA_API_KEY is required for Cricket Data ingestion")

        now = self._utc_now()
        oldest_match_datetime = now - timedelta(days=self.lookback_days)
        current_matches = self._fetch_paginated("currentMatches", max_pages=self.max_current_pages)
        all_matches = self._fetch_paginated("matches", max_pages=self.max_match_pages)

        matches_by_id: dict[str, CricketDataMatch] = {}
        for match in current_matches:
            match["is_current"] = True
            matches_by_id[match["id"]] = match

        for match in all_matches:
            match["is_current"] = False
            match_datetime = self._match_datetime(match)
            if (
                match_datetime is not None
                and oldest_match_datetime <= match_datetime <= now
            ):
                matches_by_id.setdefault(match["id"], match)

        matches = list(matches_by_id.values())
        matches.sort(key=self._sort_score, reverse=True)
        return matches[:limit]

    def _fetch_paginated(self, endpoint: str, *, max_pages: int) -> list[CricketDataMatch]:
        matches: list[CricketDataMatch] = []

        for page in range(max_pages):
            offset = page * self.page_size
            payload = self._fetch_page(endpoint, offset=offset)
            raw_matches = payload.get("data")
            if not isinstance(raw_matches, list):
                return matches

            for item in raw_matches:
                if not isinstance(item, dict):
                    continue
                match = self._parse_match(cast(dict[str, Any], item))
                if match is not None:
                    matches.append(match)

            info = payload.get("info")
            total_rows = info.get("totalRows") if isinstance(info, dict) else None
            if not isinstance(total_rows, int) or offset + self.page_size >= total_rows:
                break

        return matches

    def _fetch_page(self, endpoint: str, *, offset: int) -> dict[str, Any]:
        response = self.session.get(
            f"{self.api_base_url}/{endpoint}",
            params={
                "apikey": self.api_key,
                "offset": offset,
            },
            timeout=self.request_timeout_seconds,
            headers={"Accept": "application/json"},
        )
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise RuntimeError(
                f"Cricket Data {endpoint} request failed with HTTP {response.status_code}: "
                f"{response.text[:300]}"
            ) from exc

        payload = cast(object, response.json())
        if not isinstance(payload, dict):
            raise ValueError(f"Cricket Data {endpoint} response was not an object")

        status = payload.get("status")
        if status != "success":
            raise RuntimeError(f"Cricket Data {endpoint} request failed: {payload}")

        return cast(dict[str, Any], payload)

    def normalise(
        self,
        raw_item: CricketDataMatch,
        category: Category,
        *,
        rank: int,
    ) -> NormalizedTrendItem:
        teams = raw_item.get("teams", [])
        team_a = teams[0] if len(teams) >= 1 else None
        team_b = teams[1] if len(teams) >= 2 else None
        score_text = self._score_text(raw_item)

        return NormalizedTrendItem(
            title=raw_item["name"],
            url=self.source_home_url,
            external_url=None,
            score=self._sort_score(raw_item),
            score_label=self._score_label(raw_item),
            rank=rank,
            metadata={
                "match_id": raw_item["id"],
                "match_type": raw_item.get("matchType"),
                "venue": raw_item.get("venue"),
                "status": raw_item["status"],
                "status_label": self._status_label(raw_item),
                "score_text": score_text,
                "date": raw_item.get("date"),
                "date_time_gmt": raw_item.get("dateTimeGMT"),
                "teams": teams,
                "team_a": team_a,
                "team_b": team_b,
                "series_id": raw_item.get("series_id"),
                "is_current": raw_item["is_current"],
                "fantasy_enabled": raw_item.get("fantasyEnabled"),
            },
        )

    def _parse_match(self, raw_item: dict[str, Any]) -> CricketDataMatch | None:
        match_id = raw_item.get("id")
        name = raw_item.get("name")
        status = raw_item.get("status")

        if not isinstance(match_id, str) or not match_id.strip():
            return None
        if not isinstance(name, str) or not name.strip():
            return None
        if not isinstance(status, str):
            return None

        match = CricketDataMatch(
            id=match_id.strip(),
            name=name.strip(),
            status=status.strip(),
            is_current=False,
        )

        for key in ("matchType", "venue", "date", "dateTimeGMT", "series_id"):
            value = raw_item.get(key)
            if isinstance(value, str) and value.strip():
                match[key] = value.strip()

        teams = raw_item.get("teams")
        if isinstance(teams, list):
            parsed_teams = [team.strip() for team in teams if isinstance(team, str) and team.strip()]
            if parsed_teams:
                match["teams"] = parsed_teams

        score = raw_item.get("score")
        if isinstance(score, list):
            parsed_score = [
                parsed_part
                for item in score
                if isinstance(item, dict)
                and (parsed_part := self._parse_score_part(cast(dict[str, Any], item))) is not None
            ]
            if parsed_score:
                match["score"] = parsed_score

        fantasy_enabled = raw_item.get("fantasyEnabled")
        if isinstance(fantasy_enabled, bool):
            match["fantasyEnabled"] = fantasy_enabled

        return match

    def _parse_score_part(self, raw_score: dict[str, Any]) -> CricketDataScore | None:
        score_part = CricketDataScore()

        runs = raw_score.get("r")
        wickets = raw_score.get("w")
        overs = raw_score.get("o")
        inning = raw_score.get("inning")

        if isinstance(runs, int):
            score_part["r"] = runs
        if isinstance(wickets, int):
            score_part["w"] = wickets
        if isinstance(overs, int | float | str):
            score_part["o"] = overs
        if isinstance(inning, str) and inning.strip():
            score_part["inning"] = inning.strip()

        return score_part if score_part else None

    def _sort_score(self, raw_item: CricketDataMatch) -> int:
        score = self._timestamp_score(raw_item)
        if raw_item["is_current"]:
            score += self.current_match_score_bonus
        return score

    def _timestamp_score(self, raw_item: CricketDataMatch) -> int:
        match_datetime = self._match_datetime(raw_item)
        if match_datetime is None:
            return 0
        return int(match_datetime.timestamp())

    def _match_datetime(self, raw_item: CricketDataMatch) -> datetime | None:
        raw_datetime = raw_item.get("dateTimeGMT")
        if isinstance(raw_datetime, str):
            parsed_datetime = parse_datetime(raw_datetime)
            if parsed_datetime is not None:
                if parsed_datetime.tzinfo is None:
                    parsed_datetime = parsed_datetime.replace(tzinfo=UTC)
                return parsed_datetime.astimezone(UTC)

        raw_date = raw_item.get("date")
        if isinstance(raw_date, str):
            parsed_date = parse_date(raw_date)
            if parsed_date is not None:
                return datetime.combine(parsed_date, datetime.min.time(), tzinfo=UTC)

        return None

    def _score_label(self, raw_item: CricketDataMatch) -> str:
        label = self._status_label(raw_item)
        return label[:50]

    def _status_label(self, raw_item: CricketDataMatch) -> str:
        status = raw_item["status"].strip()
        if not status:
            return "Live" if raw_item["is_current"] else "Recent"
        return status

    def _score_text(self, raw_item: CricketDataMatch) -> str | None:
        score_parts = raw_item.get("score")
        if not score_parts:
            return None

        parts: list[str] = []
        for score_part in score_parts[:2]:
            inning = score_part.get("inning")
            runs = score_part.get("r")
            wickets = score_part.get("w")
            overs = score_part.get("o")
            if inning and runs is not None and wickets is not None:
                text = f"{inning}: {runs}/{wickets}"
                if overs is not None:
                    text = f"{text} ({overs} ov)"
                parts.append(text)

        return "; ".join(parts) if parts else None

    def _utc_now(self) -> datetime:
        return datetime.now(UTC)
