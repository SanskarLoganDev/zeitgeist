"""
Fetch top DEV articles using the public Forem API.

DEV provides real engagement fields (`public_reactions_count` and
`comments_count`), which makes it a better Tech trend source than APIs that
only expose recency.
"""
from __future__ import annotations

from typing import Any, NotRequired, TypedDict, cast

import requests  # type: ignore[import-untyped]

from apps.categories.models import Category
from apps.ingestion.adapters.base import BaseSourceAdapter, NormalizedTrendItem


class DevToArticle(TypedDict):
    id: int
    title: str
    url: str
    public_reactions_count: NotRequired[int]
    comments_count: NotRequired[int]
    canonical_url: NotRequired[str | None]
    tag_list: NotRequired[list[str]]


class DevToAdapter(BaseSourceAdapter[DevToArticle]):
    source_name = "devto"
    articles_url = "https://dev.to/api/articles"
    top_days = 30
    request_timeout_seconds = 10

    def __init__(self, session: requests.Session | None = None) -> None:
        self.session = session or requests.Session()

    @classmethod
    def get_source_name(cls) -> str:
        return cls.source_name

    def fetch(self, category: Category, *, limit: int = 50) -> list[DevToArticle]:
        response = self.session.get(
            self.articles_url,
            params={
                "top": self.top_days,
                "per_page": limit,
            },
            timeout=self.request_timeout_seconds,
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        payload = cast(object, response.json())

        if not isinstance(payload, list):
            raise ValueError("DEV articles response was not a list")

        articles: list[DevToArticle] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            article = self._parse_article(cast(dict[str, Any], item))
            if article is not None:
                articles.append(article)

        return articles[:limit]

    def normalise(
        self,
        raw_item: DevToArticle,
        category: Category,
        *,
        rank: int,
    ) -> NormalizedTrendItem:
        reactions = raw_item.get("public_reactions_count", 0)
        comments = raw_item.get("comments_count", 0)
        canonical_url = raw_item.get("canonical_url")

        return NormalizedTrendItem(
            title=raw_item["title"],
            url=raw_item["url"],
            external_url=canonical_url or raw_item["url"],
            score=reactions + comments,
            score_label="engagement",
            rank=rank,
        )

    def _parse_article(self, raw_item: dict[str, Any]) -> DevToArticle | None:
        article_id = raw_item.get("id")
        title = raw_item.get("title")
        url = raw_item.get("url")

        if not isinstance(article_id, int):
            return None
        if not isinstance(title, str) or not title.strip():
            return None
        if not isinstance(url, str) or not url.strip():
            return None

        article = DevToArticle(
            id=article_id,
            title=title.strip(),
            url=url.strip(),
        )

        public_reactions_count = raw_item.get("public_reactions_count")
        if isinstance(public_reactions_count, int):
            article["public_reactions_count"] = public_reactions_count

        comments_count = raw_item.get("comments_count")
        if isinstance(comments_count, int):
            article["comments_count"] = comments_count

        canonical_url = raw_item.get("canonical_url")
        if isinstance(canonical_url, str) and canonical_url.strip():
            article["canonical_url"] = canonical_url.strip()

        tag_list = raw_item.get("tag_list")
        if isinstance(tag_list, list) and all(isinstance(tag, str) for tag in tag_list):
            article["tag_list"] = tag_list

        return article
