"""
backend/apps/ingestion/adapters/hackernews.py
──────────────────────────────────────────────
Purpose : Fetches top stories from Hacker News using the official Firebase API.
          The HN API is completely free, requires no authentication, and has no
          documented rate limit — making it the most reliable source in the pipeline.

          Endpoint used:
            https://hacker-news.firebaseio.com/v0/topstories.json  → list of top story IDs
            https://hacker-news.firebaseio.com/v0/item/{id}.json   → story detail

          Normalised fields:
            title        → story title
            url          → the URL the story links to (external article/repo)
            source       → "hackernews"
            score        → HN points
            score_label  → "points"

          Used for: Tech and Research categories primarily.
          HN aggregates the highest-quality tech/research links from the community —
          a strong signal that complements Reddit's broader discussion volume.

Used by : apps/ingestion/orchestrator.py — instantiated for categories where
            CategorySourceConfig has source="hackernews"

Phase    : 1 — Week 2
"""
from __future__ import annotations

from typing import Any, NotRequired, TypedDict, cast

import requests  # type: ignore[import-untyped]

from apps.categories.models import Category
from apps.ingestion.adapters.base import BaseSourceAdapter, NormalizedTrendItem


class HackerNewsItem(TypedDict):
    id: int
    title: str
    score: NotRequired[int]
    type: NotRequired[str]
    url: NotRequired[str]
    deleted: NotRequired[bool]
    dead: NotRequired[bool]


class HackerNewsAdapter(BaseSourceAdapter[HackerNewsItem]):
    source_name = "hackernews"
    top_stories_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
    item_url_template = "https://hacker-news.firebaseio.com/v0/item/{item_id}.json"
    discussion_url_template = "https://news.ycombinator.com/item?id={item_id}"
    request_timeout_seconds = 10

    def __init__(self, session: requests.Session | None = None) -> None:
        self.session = session or requests.Session()

    @classmethod
    def get_source_name(cls) -> str:
        return cls.source_name

    def fetch(self, category: Category, *, limit: int = 20) -> list[HackerNewsItem]:
        top_story_ids = self._fetch_top_story_ids()
        stories: list[HackerNewsItem] = []

        for item_id in top_story_ids:
            item = self._fetch_item(item_id)
            if item is None:
                continue
            stories.append(item)
            if len(stories) >= limit:
                break

        return stories

    def normalise(
        self,
        raw_item: HackerNewsItem,
        category: Category,
        *,
        rank: int,
    ) -> NormalizedTrendItem:
        discussion_url = self.discussion_url_template.format(item_id=raw_item["id"])
        external_url = raw_item.get("url")

        return NormalizedTrendItem(
            title=raw_item["title"],
            url=discussion_url,
            external_url=external_url,
            score=raw_item.get("score", 0),
            score_label="points",
            rank=rank,
        )

    def _fetch_top_story_ids(self) -> list[int]:
        response = self.session.get(
            self.top_stories_url,
            timeout=self.request_timeout_seconds,
        )
        response.raise_for_status()
        payload = cast(object, response.json())

        if not isinstance(payload, list):
            raise ValueError("Hacker News topstories response was not a list")

        story_ids: list[int] = []
        for item in payload:
            if isinstance(item, int):
                story_ids.append(item)

        return story_ids

    def _fetch_item(self, item_id: int) -> HackerNewsItem | None:
        response = self.session.get(
            self.item_url_template.format(item_id=item_id),
            timeout=self.request_timeout_seconds,
        )
        response.raise_for_status()
        payload = cast(object, response.json())

        if not isinstance(payload, dict):
            return None

        raw_item = cast(dict[str, Any], payload)
        if raw_item.get("type") != "story":
            return None
        if raw_item.get("deleted") is True or raw_item.get("dead") is True:
            return None

        title = raw_item.get("title")
        if not isinstance(title, str) or not title.strip():
            return None

        item_payload = HackerNewsItem(id=item_id, title=title.strip(), type="story")

        score = raw_item.get("score")
        if isinstance(score, int):
            item_payload["score"] = score

        url = raw_item.get("url")
        if isinstance(url, str) and url.strip():
            item_payload["url"] = url.strip()

        return item_payload
