"""Vertex AI / Gemini client helpers used by batch jobs only."""
from __future__ import annotations

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
        trend_items=_format_trend_items(trend_items),
    )


def _format_trend_items(trend_items: list[SummaryTrendItem]) -> str:
    if not trend_items:
        return "No trend items are available."

    return "\n".join(
        f"- {item.source}: {item.title}"
        for item in trend_items
    )
