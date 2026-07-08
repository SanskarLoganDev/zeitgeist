from __future__ import annotations

from datetime import date
from typing import Any, cast

import pytest

from apps.categories.models import Category
from apps.ingestion.adapters.football_data import FootballDataAdapter, FootballDataMatch


class FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.status_code = 200
        self.text = ""

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self.payload


class FakeSession:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.last_headers: dict[str, str] | None = None
        self.last_params: dict[str, str] | None = None
        self.all_params: list[dict[str, str]] = []

    def get(
        self,
        url: str,
        *,
        params: dict[str, str],
        headers: dict[str, str],
        timeout: int,
    ) -> FakeResponse:
        del url, timeout
        self.last_params = params
        self.all_params.append(params)
        self.last_headers = headers
        return FakeResponse(self.payload)


def test_football_data_fetches_last_10_utc_days_and_sorts_recent_matches_first(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = FakeSession(
        {
            "matches": [
                raw_football_match(match_id=1, utc_date="2026-07-06T19:00:00Z"),
                raw_football_match(match_id=2, utc_date="2026-07-07T20:00:00Z"),
            ]
        }
    )
    adapter = FootballDataAdapter(session=cast(Any, session), api_key="test-token")
    monkeypatch.setattr(adapter, "_utc_today", lambda: date(2026, 7, 8))

    matches = adapter.fetch(Category(name="Sports", slug="sports"), limit=50)

    assert [match["id"] for match in matches] == [2, 1]
    assert session.all_params == [
        {"dateFrom": "2026-06-29", "dateTo": "2026-07-08"},
    ]
    assert session.last_headers == {
        "Accept": "application/json",
        "X-Auth-Token": "test-token",
    }


def test_football_data_normalise_preserves_match_display_metadata() -> None:
    adapter = FootballDataAdapter(api_key="test-token")
    item = adapter.normalise(
        parsed_football_match(
            match_id=537382,
            utc_date="2026-07-07T20:00:00Z",
            home_team="Switzerland",
            away_team="Colombia",
            home_score=0,
            away_score=0,
            full_time_home_score=4,
            full_time_away_score=3,
            duration="PENALTY_SHOOTOUT",
            stage="LAST_16",
            penalty_home_score=4,
            penalty_away_score=3,
        ),
        Category(name="Sports", slug="sports"),
        rank=1,
    )

    assert item.title == "Switzerland vs Colombia"
    assert item.score_label == "Full-time - 0-0 pens 4-3"
    assert item.score > 0
    assert item.metadata["competition_name"] == "FIFA World Cup"
    assert item.metadata["home_team"] == "Switzerland"
    assert item.metadata["away_team"] == "Colombia"
    assert item.metadata["home_score"] == 0
    assert item.metadata["away_score"] == 0
    assert item.metadata["stage_label"] == "Round of 16"
    assert item.metadata["penalty_home_score"] == 4
    assert item.metadata["penalty_away_score"] == 3


def parsed_football_match(
    *,
    match_id: int,
    utc_date: str,
    home_team: str = "Argentina",
    away_team: str = "Egypt",
    home_score: int = 3,
    away_score: int = 2,
    full_time_home_score: int | None = None,
    full_time_away_score: int | None = None,
    duration: str = "REGULAR",
    stage: str = "LAST_16",
    penalty_home_score: int | None = None,
    penalty_away_score: int | None = None,
) -> FootballDataMatch:
    full_time_home = full_time_home_score if full_time_home_score is not None else home_score
    full_time_away = full_time_away_score if full_time_away_score is not None else away_score
    score = {
        "winner": "HOME_TEAM",
        "duration": duration,
        "fullTime": {"home": full_time_home, "away": full_time_away},
        "halfTime": {"home": 0, "away": 1},
        "regularTime": {"home": home_score, "away": away_score},
    }
    if penalty_home_score is not None or penalty_away_score is not None:
        score["penalties"] = {
            "home": penalty_home_score,
            "away": penalty_away_score,
        }

    return cast(
        FootballDataMatch,
        {
            "id": match_id,
            "utcDate": utc_date,
            "status": "FINISHED",
            "stage": stage,
            "competition_name": "FIFA World Cup",
            "competition_code": "WC",
            "home_team": home_team,
            "away_team": away_team,
            "score": score,
            "lastUpdated": "2026-07-08T08:25:01Z",
        },
    )


def raw_football_match(
    *,
    match_id: int,
    utc_date: str,
    home_team: str = "Argentina",
    away_team: str = "Egypt",
    home_score: int = 3,
    away_score: int = 2,
    duration: str = "REGULAR",
    stage: str = "LAST_16",
    penalty_home_score: int | None = None,
    penalty_away_score: int | None = None,
) -> dict[str, Any]:
    score: dict[str, Any] = {
        "winner": "HOME_TEAM",
        "duration": duration,
        "fullTime": {"home": home_score, "away": away_score},
        "halfTime": {"home": 0, "away": 1},
    }
    if penalty_home_score is not None or penalty_away_score is not None:
        score["penalties"] = {
            "home": penalty_home_score,
            "away": penalty_away_score,
        }

    return {
        "id": match_id,
        "utcDate": utc_date,
        "status": "FINISHED",
        "stage": stage,
        "competition": {
            "id": 2000,
            "name": "FIFA World Cup",
            "code": "WC",
            "type": "CUP",
        },
        "homeTeam": {"id": 762, "name": home_team},
        "awayTeam": {"id": 825, "name": away_team},
        "score": score,
        "lastUpdated": "2026-07-08T08:25:01Z",
    }
