from __future__ import annotations

from dataclasses import dataclass

import pytest

from apps.ai.client import GeminiClient, SummaryTrendItem, build_category_summary_prompt
from apps.ai.sanitizers import sanitize_category_summary


@dataclass
class FakeResponse:
    text: str


class FakeModelClient:
    def __init__(self) -> None:
        self.last_model: str | None = None
        self.last_contents: str | None = None

    def generate_content(self, *, model: str, contents: str) -> FakeResponse:
        self.last_model = model
        self.last_contents = contents
        return FakeResponse(text="AI tools and browser APIs are leading the tech conversation.")


def test_build_category_summary_prompt_includes_category_and_items() -> None:
    prompt = build_category_summary_prompt(
        category_name="Tech",
        trend_items=[
            SummaryTrendItem(
                source="hackernews",
                rank=1,
                title="SQLite on the server",
                score_label="512 points",
            )
        ],
    )

    assert 'summary for "Tech"' in prompt
    assert "Source: Hacker News" in prompt
    assert "Title: SQLite on the server" in prompt
    assert "Signal: 512 points" in prompt
    assert "under 120 words" in prompt


def test_build_category_summary_prompt_includes_sports_metadata() -> None:
    prompt = build_category_summary_prompt(
        category_name="Sports",
        trend_items=[
            SummaryTrendItem(
                source="football_data",
                rank=1,
                title="Argentina vs Switzerland",
                score_label="Full-time - 3-1",
                metadata={
                    "competition_name": "UEFA Women's Euro",
                    "home_team": "Argentina",
                    "away_team": "Switzerland",
                    "home_score": 3,
                    "away_score": 1,
                    "status_label": "Full-time",
                },
            )
        ],
    )

    assert "If a match is finished, mention the winner and score" in prompt
    assert "Competition: UEFA Women's Euro" in prompt
    assert "Score: Argentina 3-1 Switzerland" in prompt
    assert "exactly 2 bullet points" in prompt


def test_build_category_summary_prompt_includes_cricket_metadata() -> None:
    prompt = build_category_summary_prompt(
        category_name="Sports",
        trend_items=[
            SummaryTrendItem(
                source="cricket_data",
                rank=1,
                title="Sri Lanka vs Bangladesh, 2nd ODI",
                score_label="Sri Lanka won by 5 wickets",
                metadata={
                    "match_type": "odi",
                    "team_a": "Sri Lanka",
                    "team_b": "Bangladesh",
                    "status_label": "Sri Lanka won by 5 wickets",
                    "score_text": "Sri Lanka Inning 1: 245/5 (48.1 ov)",
                    "venue": "R Premadasa Stadium",
                },
            )
        ],
    )

    assert "Source: Cricket Data" in prompt
    assert "Match type: ODI" in prompt
    assert "Teams: Sri Lanka vs Bangladesh" in prompt
    assert "Score: Sri Lanka Inning 1: 245/5 (48.1 ov)" in prompt


def test_gemini_client_uses_model_client_and_strips_response() -> None:
    fake_model_client = FakeModelClient()
    client = GeminiClient(model_name="gemini-test", model_client=fake_model_client)

    summary = client.generate_category_summary(
        category_name="Tech",
        trend_items=[
            SummaryTrendItem(
                source="devto",
                rank=1,
                title="Practical browser APIs",
                score_label="100 engagement",
            )
        ],
    )

    assert summary == "AI tools and browser APIs are leading the tech conversation."
    assert fake_model_client.last_model == "gemini-test"
    assert fake_model_client.last_contents is not None
    assert "Practical browser APIs" in fake_model_client.last_contents


def test_gemini_client_removes_degenerate_summary_tokens() -> None:
    class DegenerateModelClient:
        def generate_content(self, *, model: str, contents: str) -> FakeResponse:
            del model, contents
            return FakeResponse(
                text="News topics are shifting. news.of_0_0_0_0_0_0_0_0_0_0_0_0"
            )

    client = GeminiClient(model_name="gemini-test", model_client=DegenerateModelClient())

    summary = client.generate_category_summary(category_name="News", trend_items=[])

    assert summary == "News topics are shifting."


def test_sanitize_category_summary_removes_stored_generation_artifacts() -> None:
    summary = sanitize_category_summary(
        "Coverage is broad. news.of_0_0_0_0_0_0_0_0_0_0_0_0"
    )

    assert summary == "Coverage is broad."


def test_gemini_client_rejects_empty_response() -> None:
    class EmptyModelClient:
        def generate_content(self, *, model: str, contents: str) -> FakeResponse:
            del model, contents
            return FakeResponse(text=" ")

    client = GeminiClient(model_name="gemini-test", model_client=EmptyModelClient())

    with pytest.raises(RuntimeError, match="empty category summary"):
        client.generate_category_summary(category_name="Tech", trend_items=[])
