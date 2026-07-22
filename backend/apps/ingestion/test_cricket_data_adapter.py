from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast

import pytest

from apps.categories.models import Category
from apps.ingestion.adapters.cricket_data import CricketDataAdapter


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
    def __init__(self, payloads: dict[str, dict[str, Any]]) -> None:
        self.payloads = payloads
        self.calls: list[tuple[str, dict[str, str | int], dict[str, str]]] = []

    def get(
        self,
        url: str,
        *,
        params: dict[str, str | int | None],
        headers: dict[str, str],
        timeout: int,
    ) -> FakeResponse:
        del timeout
        endpoint = url.rsplit("/", maxsplit=1)[-1]
        offset = params["offset"]
        key = f"{endpoint}:{offset}"
        self.calls.append((endpoint, cast(dict[str, str | int], params), headers))
        return FakeResponse(self.payloads[key])


def test_cricket_data_fetches_current_and_past_matches_without_future_fixtures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = FakeSession(
        {
            "currentMatches:0": success_payload(
                [
                    raw_cricket_match(
                        match_id="current-1",
                        name="India vs England, 3rd Test",
                        status="Day 2: India trail by 120 runs",
                        date_time_gmt="2026-07-22T10:00:00",
                    )
                ],
                total_rows=1,
            ),
            "matches:0": success_payload(
                [
                    raw_cricket_match(
                        match_id="past-1",
                        name="Sri Lanka vs Bangladesh, 2nd ODI",
                        status="Sri Lanka won by 5 wickets",
                        date_time_gmt="2026-07-21T14:00:00",
                    ),
                    raw_cricket_match(
                        match_id="future-1",
                        name="Australia vs Pakistan, 1st T20I",
                        status="Match not started",
                        date_time_gmt="2026-07-24T14:00:00",
                    ),
                    raw_cricket_match(
                        match_id="old-1",
                        name="West Indies vs New Zealand, 1st T20I",
                        status="New Zealand won by 8 runs",
                        date_time_gmt="2026-07-07T14:00:00",
                    ),
                    raw_cricket_match(
                        match_id="current-1",
                        name="India vs England, 3rd Test",
                        status="Day 2: India trail by 120 runs",
                        date_time_gmt="2026-07-22T10:00:00",
                    ),
                ],
                total_rows=3,
            ),
        }
    )
    adapter = CricketDataAdapter(session=cast(Any, session), api_key="test-token")
    monkeypatch.setattr(adapter, "_utc_now", lambda: datetime(2026, 7, 22, 15, tzinfo=UTC))

    matches = adapter.fetch(Category(name="Sports", slug="sports"), limit=50)

    assert [match["id"] for match in matches] == ["current-1", "past-1"]
    assert matches[0]["is_current"] is True
    assert session.calls == [
        (
            "currentMatches",
            {"apikey": "test-token", "offset": 0},
            {"Accept": "application/json"},
        ),
        (
            "matches",
            {"apikey": "test-token", "offset": 0},
            {"Accept": "application/json"},
        ),
    ]


def test_cricket_data_collects_up_to_50_recent_matches_from_multiple_pages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_matches = [
        raw_cricket_match(
            match_id=f"past-{index}",
            name=f"Team {index} vs Team {index + 1}",
            status="Team won",
            date_time_gmt=f"2026-07-{22 - (index // 8):02d}T{23 - (index % 8):02d}:00:00",
        )
        for index in range(60)
    ]
    session = FakeSession(
        {
            "currentMatches:0": success_payload([], total_rows=0),
            "matches:0": success_payload(raw_matches[:25], total_rows=60),
            "matches:25": success_payload(raw_matches[25:50], total_rows=60),
            "matches:50": success_payload(raw_matches[50:], total_rows=60),
        }
    )
    adapter = CricketDataAdapter(session=cast(Any, session), api_key="test-token")
    monkeypatch.setattr(adapter, "_utc_now", lambda: datetime(2026, 7, 22, 23, 30, tzinfo=UTC))

    matches = adapter.fetch(Category(name="Sports", slug="sports"), limit=50)

    assert len(matches) == 50
    assert [call[1]["offset"] for call in session.calls if call[0] == "matches"] == [0, 25, 50]


def test_cricket_data_normalise_preserves_match_display_metadata() -> None:
    adapter = CricketDataAdapter(api_key="test-token")
    item = adapter.normalise(
        cast(
            Any,
            {
                **raw_cricket_match(
                    match_id="match-1",
                    name="Sri Lanka vs Bangladesh, 2nd ODI",
                    status="Sri Lanka won by 5 wickets",
                    date_time_gmt="2026-07-21T14:00:00",
                ),
                "is_current": False,
            },
        ),
        Category(name="Sports", slug="sports"),
        rank=1,
    )

    assert item.title == "Sri Lanka vs Bangladesh, 2nd ODI"
    assert item.score_label == "Sri Lanka won by 5 wickets"
    assert item.score > 0
    assert item.metadata["team_a"] == "Sri Lanka"
    assert item.metadata["team_b"] == "Bangladesh"
    assert item.metadata["match_type"] == "odi"
    assert item.metadata["score_text"] == (
        "Sri Lanka Inning 1: 245/5 (48.1 ov); Bangladesh Inning 1: 244/9 (50 ov)"
    )


def success_payload(data: list[dict[str, Any]], *, total_rows: int) -> dict[str, Any]:
    return {
        "status": "success",
        "data": data,
        "info": {
            "offsetRows": 0,
            "totalRows": total_rows,
        },
    }


def raw_cricket_match(
    *,
    match_id: str,
    name: str,
    status: str,
    date_time_gmt: str,
) -> dict[str, Any]:
    return {
        "id": match_id,
        "name": name,
        "status": status,
        "matchType": "odi",
        "venue": "R Premadasa Stadium",
        "date": date_time_gmt[:10],
        "dateTimeGMT": date_time_gmt,
        "teams": ["Sri Lanka", "Bangladesh"],
        "series_id": "series-1",
        "fantasyEnabled": True,
        "score": [
            {
                "r": 245,
                "w": 5,
                "o": 48.1,
                "inning": "Sri Lanka Inning 1",
            },
            {
                "r": 244,
                "w": 9,
                "o": 50,
                "inning": "Bangladesh Inning 1",
            },
        ],
    }
