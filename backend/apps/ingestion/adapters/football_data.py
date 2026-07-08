"""
Fetch recent football matches using the Football-Data API.

Football-Data exposes match schedules/results rather than social popularity.
For Zeitgeist's Sports category, this adapter treats football as a recent match
feed: fetch the last 10 UTC days, sort by match time descending, and keep up to 50.
"""
from __future__ import annotations

import os
from datetime import UTC, date, datetime, timedelta
from typing import Any, NotRequired, TypedDict, cast

import requests  # type: ignore[import-untyped]
from django.utils.dateparse import parse_datetime

from apps.categories.models import Category
from apps.ingestion.adapters.base import BaseSourceAdapter, NormalizedTrendItem


class FootballDataScorePart(TypedDict, total=False):
    home: int | None
    away: int | None


class FootballDataScore(TypedDict, total=False):
    winner: str | None
    duration: str
    fullTime: FootballDataScorePart
    halfTime: FootballDataScorePart
    regularTime: FootballDataScorePart
    extraTime: FootballDataScorePart
    penalties: FootballDataScorePart


class FootballDataMatch(TypedDict):
    id: int
    utcDate: str
    status: str
    stage: NotRequired[str | None]
    competition_name: str
    competition_code: NotRequired[str | None]
    home_team: str
    away_team: str
    score: FootballDataScore
    lastUpdated: NotRequired[str | None]


class FootballDataAdapter(BaseSourceAdapter[FootballDataMatch]):
    source_name = "football_data"
    matches_url = "https://api.football-data.org/v4/matches"
    source_home_url = "https://www.football-data.org/"
    lookback_days = 10
    request_timeout_seconds = 10

    def __init__(
        self,
        session: requests.Session | None = None,
        api_key: str | None = None,
    ) -> None:
        self.session = session or requests.Session()
        self.api_key = (
            api_key if api_key is not None else os.environ.get("FOOTBALL_DATA_API_KEY")
        )

    @classmethod
    def get_source_name(cls) -> str:
        return cls.source_name

    def fetch(self, category: Category, *, limit: int = 50) -> list[FootballDataMatch]:
        if not self.api_key:
            raise RuntimeError("FOOTBALL_DATA_API_KEY is required for Football-Data ingestion")

        utc_today = self._utc_today()
        start_date = utc_today - timedelta(days=self.lookback_days - 1)
        matches = self._fetch_window(start_date, utc_today)
        matches.sort(key=lambda match: match["utcDate"], reverse=True)
        return matches[:limit]

    def _utc_today(self) -> date:
        return datetime.now(UTC).date()

    def _fetch_window(self, start_date: date, end_date: date) -> list[FootballDataMatch]:
        response = self.session.get(
            self.matches_url,
            params={
                "dateFrom": start_date.isoformat(),
                "dateTo": end_date.isoformat(),
            },
            headers={
                "Accept": "application/json",
                "X-Auth-Token": self.api_key,
            },
            timeout=self.request_timeout_seconds,
        )
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise RuntimeError(
                f"Football-Data request failed with HTTP {response.status_code}: "
                f"{response.text[:300]}"
            ) from exc
        payload = cast(object, response.json())

        if not isinstance(payload, dict):
            raise ValueError("Football-Data matches response was not an object")

        raw_matches = payload.get("matches")
        if not isinstance(raw_matches, list):
            raise ValueError("Football-Data matches response did not include a matches list")

        matches: list[FootballDataMatch] = []
        for item in raw_matches:
            if not isinstance(item, dict):
                continue
            match = self._parse_match(cast(dict[str, Any], item))
            if match is not None:
                matches.append(match)

        return matches

    def normalise(
        self,
        raw_item: FootballDataMatch,
        category: Category,
        *,
        rank: int,
    ) -> NormalizedTrendItem:
        score_label = self._score_label(raw_item)

        return NormalizedTrendItem(
            title=f"{raw_item['home_team']} vs {raw_item['away_team']}",
            url=self.source_home_url,
            external_url=None,
            score=self._timestamp_score(raw_item["utcDate"]),
            score_label=score_label,
            rank=rank,
            metadata={
                "competition_name": raw_item["competition_name"],
                "competition_code": raw_item.get("competition_code"),
                "home_team": raw_item["home_team"],
                "away_team": raw_item["away_team"],
                "home_score": self._display_score_value(raw_item, "home"),
                "away_score": self._display_score_value(raw_item, "away"),
                "status": raw_item["status"],
                "status_label": self._status_label(raw_item["status"]),
                "stage": raw_item.get("stage"),
                "stage_label": self._stage_label(raw_item.get("stage")),
                "duration": raw_item["score"].get("duration"),
                "penalty_home_score": self._score_value(raw_item, "penalties", "home"),
                "penalty_away_score": self._score_value(raw_item, "penalties", "away"),
                "utc_date": raw_item["utcDate"],
                "last_updated": raw_item.get("lastUpdated"),
            },
        )

    def _parse_match(self, raw_item: dict[str, Any]) -> FootballDataMatch | None:
        match_id = raw_item.get("id")
        utc_date = raw_item.get("utcDate")
        status = raw_item.get("status")
        competition = raw_item.get("competition")
        home_team = raw_item.get("homeTeam")
        away_team = raw_item.get("awayTeam")
        score = raw_item.get("score")

        if not isinstance(match_id, int):
            return None
        if not isinstance(utc_date, str) or parse_datetime(utc_date) is None:
            return None
        if not isinstance(status, str) or not status.strip():
            return None
        if not isinstance(competition, dict):
            return None
        if not isinstance(home_team, dict) or not isinstance(away_team, dict):
            return None
        if not isinstance(score, dict):
            return None

        competition_name = competition.get("name")
        home_team_name = home_team.get("name")
        away_team_name = away_team.get("name")
        if not isinstance(competition_name, str) or not competition_name.strip():
            return None
        if not isinstance(home_team_name, str) or not home_team_name.strip():
            return None
        if not isinstance(away_team_name, str) or not away_team_name.strip():
            return None

        match = FootballDataMatch(
            id=match_id,
            utcDate=utc_date,
            status=status.strip(),
            competition_name=competition_name.strip(),
            home_team=home_team_name.strip(),
            away_team=away_team_name.strip(),
            score=self._parse_score(cast(dict[str, Any], score)),
        )

        stage = raw_item.get("stage")
        if isinstance(stage, str) and stage.strip():
            match["stage"] = stage.strip()

        competition_code = competition.get("code")
        if isinstance(competition_code, str) and competition_code.strip():
            match["competition_code"] = competition_code.strip()

        last_updated = raw_item.get("lastUpdated")
        if isinstance(last_updated, str) and last_updated.strip():
            match["lastUpdated"] = last_updated.strip()

        return match

    def _parse_score(self, raw_score: dict[str, Any]) -> FootballDataScore:
        score = FootballDataScore()

        winner = raw_score.get("winner")
        if isinstance(winner, str) or winner is None:
            score["winner"] = winner

        duration = raw_score.get("duration")
        if isinstance(duration, str):
            score["duration"] = duration

        for key in ("fullTime", "halfTime", "regularTime", "extraTime", "penalties"):
            value = raw_score.get(key)
            if isinstance(value, dict):
                score[key] = self._parse_score_part(cast(dict[str, Any], value))

        return score

    def _parse_score_part(self, raw_score_part: dict[str, Any]) -> FootballDataScorePart:
        score_part = FootballDataScorePart()
        home_score = raw_score_part.get("home")
        away_score = raw_score_part.get("away")

        if isinstance(home_score, int) or home_score is None:
            score_part["home"] = home_score
        if isinstance(away_score, int) or away_score is None:
            score_part["away"] = away_score

        return score_part

    def _timestamp_score(self, utc_date: str) -> int:
        parsed_date = parse_datetime(utc_date)
        if parsed_date is None:
            return 0
        return int(parsed_date.timestamp())

    def _score_value(
        self,
        raw_item: FootballDataMatch,
        score_part: str,
        side: str,
    ) -> int | None:
        raw_score_part = raw_item["score"].get(score_part)
        if not isinstance(raw_score_part, dict):
            return None

        value = raw_score_part.get(side)
        return value if isinstance(value, int) else None

    def _display_score_value(self, raw_item: FootballDataMatch, side: str) -> int | None:
        penalty_home = self._score_value(raw_item, "penalties", "home")
        penalty_away = self._score_value(raw_item, "penalties", "away")
        regular_time_value = self._score_value(raw_item, "regularTime", side)

        if (
            penalty_home is not None
            and penalty_away is not None
            and regular_time_value is not None
        ):
            return regular_time_value

        return self._score_value(raw_item, "fullTime", side)

    def _score_label(self, raw_item: FootballDataMatch) -> str:
        display_home = self._display_score_value(raw_item, "home")
        display_away = self._display_score_value(raw_item, "away")
        status_label = self._status_label(raw_item["status"])

        if display_home is None or display_away is None:
            return status_label

        score_label = f"{status_label} - {display_home}-{display_away}"
        penalty_home = self._score_value(raw_item, "penalties", "home")
        penalty_away = self._score_value(raw_item, "penalties", "away")
        if penalty_home is not None and penalty_away is not None:
            score_label = f"{score_label} pens {penalty_home}-{penalty_away}"

        return score_label

    def _status_label(self, status: str) -> str:
        return {
            "FINISHED": "Full-time",
            "IN_PLAY": "Live",
            "PAUSED": "Paused",
            "TIMED": "Scheduled",
            "SCHEDULED": "Scheduled",
            "POSTPONED": "Postponed",
            "CANCELLED": "Cancelled",
            "SUSPENDED": "Suspended",
        }.get(status, status.replace("_", " ").title())

    def _stage_label(self, stage: str | None) -> str | None:
        if stage is None:
            return None
        return {
            "GROUP_STAGE": "Group stage",
            "LAST_16": "Round of 16",
            "ROUND_OF_16": "Round of 16",
            "QUARTER_FINALS": "Quarter-finals",
            "SEMI_FINALS": "Semi-finals",
            "FINAL": "Final",
        }.get(stage, stage.replace("_", " ").title())
