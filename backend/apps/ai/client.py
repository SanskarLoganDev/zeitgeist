"""Vertex AI / Gemini client helpers used by batch jobs only."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from django.conf import settings

from apps.ai.prompts import CATEGORY_SUMMARY_PROMPT
from apps.ai.sanitizers import sanitize_category_summary

MAX_PROMPT_ITEMS = 12


@dataclass(frozen=True)
class SummaryTrendItem:
    """Minimal trend item shape sent to Gemini."""

    source: str
    rank: int
    title: str
    score_label: str
    metadata: Mapping[str, object] | None = None


class GenAIModelClient(Protocol):
    def generate_content(self, *, model: str, contents: str) -> object: ...


class GeminiClient:
    """Small wrapper around the Google Gen AI SDK.

    Cloud Run authenticates through the attached service account and environment
    variables such as GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION.
    """

    def __init__(
        self,
        *,
        model_name: str | None = None,
        model_client: GenAIModelClient | None = None,
    ) -> None:
        self.model_name = model_name or settings.GEMINI_MODEL
        self._model_client = model_client
        self._client: Any | None = None

    def generate_category_summary(
        self,
        *,
        category_name: str,
        trend_items: list[SummaryTrendItem],
    ) -> str:
        prompt = build_category_summary_prompt(
            category_name=category_name,
            trend_items=trend_items[:MAX_PROMPT_ITEMS],
        )
        response = self._get_model_client().generate_content(
            model=self.model_name,
            contents=prompt,
        )
        text = getattr(response, "text", None)
        if not isinstance(text, str) or not text.strip():
            raise RuntimeError("Gemini returned an empty category summary")

        summary = sanitize_category_summary(text)
        if not summary:
            raise RuntimeError("Gemini returned an empty category summary")

        return summary

    def _get_model_client(self) -> GenAIModelClient:
        if self._model_client is not None:
            return self._model_client

        try:
            from google import genai
            from google.genai.types import HttpOptions
        except ImportError as exc:
            raise RuntimeError("google-genai is required for AI summary generation") from exc

        self._client = genai.Client(http_options=HttpOptions(api_version="v1"))
        self._model_client = self._client.models
        return self._model_client


def build_category_summary_prompt(
    *,
    category_name: str,
    trend_items: list[SummaryTrendItem],
) -> str:
    return CATEGORY_SUMMARY_PROMPT.format(
        category_name=category_name,
        category_guidance=_category_guidance(category_name),
        trend_items=_format_trend_items(trend_items),
    )


def _format_trend_items(trend_items: list[SummaryTrendItem]) -> str:
    if not trend_items:
        return "No trend items are available."

    return "\n\n".join(_format_trend_item(item) for item in trend_items)


def _format_trend_item(item: SummaryTrendItem) -> str:
    lines = [
        f"- Source: {_source_label(item.source)}",
        f"  Rank: {item.rank}",
        f"  Title: {item.title}",
        f"  Signal: {item.score_label}",
    ]
    details = _metadata_details(item)
    if details:
        lines.append(f"  Details: {details}")
    return "\n".join(lines)


def _metadata_details(item: SummaryTrendItem) -> str:
    metadata = item.metadata or {}

    if item.source == "football_data":
        parts = _football_details(metadata)
    elif item.source == "cricket_data":
        parts = _cricket_details(metadata)
    else:
        parts = _generic_metadata_details(metadata)

    return "; ".join(parts[:5])


def _football_details(metadata: Mapping[str, object]) -> list[str]:
    parts: list[str] = []
    competition = _string_metadata(metadata, "competition_name")
    status = _string_metadata(metadata, "status_label")
    stage = _string_metadata(metadata, "stage_label")
    home_team = _string_metadata(metadata, "home_team")
    away_team = _string_metadata(metadata, "away_team")
    home_score = _int_metadata(metadata, "home_score")
    away_score = _int_metadata(metadata, "away_score")

    if competition:
        parts.append(f"Competition: {competition}")
    if stage:
        parts.append(f"Stage: {stage}")
    if status:
        parts.append(f"Status: {status}")
    if home_team and away_team and home_score is not None and away_score is not None:
        parts.append(f"Score: {home_team} {home_score}-{away_score} {away_team}")

    return parts


def _cricket_details(metadata: Mapping[str, object]) -> list[str]:
    parts: list[str] = []
    match_type = _string_metadata(metadata, "match_type")
    status = _string_metadata(metadata, "status_label")
    score_text = _string_metadata(metadata, "score_text")
    venue = _string_metadata(metadata, "venue")
    team_a = _string_metadata(metadata, "team_a")
    team_b = _string_metadata(metadata, "team_b")

    if match_type:
        parts.append(f"Match type: {match_type.upper()}")
    if team_a and team_b:
        parts.append(f"Teams: {team_a} vs {team_b}")
    if status:
        parts.append(f"Status: {status}")
    if score_text:
        parts.append(f"Score: {score_text}")
    if venue:
        parts.append(f"Venue: {venue}")

    return parts


def _generic_metadata_details(metadata: Mapping[str, object]) -> list[str]:
    allowed_keys = ("published_date", "released", "ratings_count")
    parts: list[str] = []
    for key in allowed_keys:
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            parts.append(f"{key.replace('_', ' ').title()}: {value.strip()}")
        elif isinstance(value, int):
            parts.append(f"{key.replace('_', ' ').title()}: {value}")
    return parts


def _category_guidance(category_name: str) -> str:
    guidance_by_category = {
        "gaming": (
            "Focus on player interest, releases, sequels, ratings, and adds. "
            "If the signal is adds, describe it as player interest."
        ),
        "news": (
            "Focus on public storylines and the people, places, or institutions named in titles. "
            "Do not sensationalize tragedy."
        ),
        "sports": (
            "Focus on matchups, results, scorelines, competitions, and form. "
            "If a match is finished, mention the winner and score. "
            "If a match is scheduled, describe it as upcoming."
        ),
        "tech": (
            "Focus on developer interest, tools, platforms, AI, infrastructure, programming, and security. "
            "Prefer concrete technology names over broad phrases."
        ),
    }
    return guidance_by_category.get(
        category_name.lower(),
        "Focus on concrete topics from the provided titles and explain why they stand out.",
    )


def _source_label(source: str) -> str:
    return {
        "cricket_data": "Cricket Data",
        "devto": "DEV",
        "football_data": "Football-Data",
        "hackernews": "Hacker News",
        "nytimes": "New York Times",
        "rawg": "RAWG",
    }.get(source, source)


def _string_metadata(metadata: Mapping[str, object], key: str) -> str | None:
    value = metadata.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _int_metadata(metadata: Mapping[str, object], key: str) -> int | None:
    value = metadata.get(key)
    if isinstance(value, int):
        return value
    return None
