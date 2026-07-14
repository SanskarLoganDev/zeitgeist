"""
Fetch most viewed New York Times articles using the Most Popular API.

NYT returns articles ranked by popularity for a chosen period. The API does not
expose raw view counts, so this adapter turns rank into a simple numeric score
while preserving the source label as "most viewed".
"""
from __future__ import annotations

import os
from typing import Any, NotRequired, TypedDict, cast

import requests

from apps.categories.models import Category
from apps.ingestion.adapters.base import BaseSourceAdapter, NormalizedTrendItem


class NYTimesArticle(TypedDict):
    id: int
    title: str
    url: str
    abstract: NotRequired[str]
    published_date: NotRequired[str]


class NYTimesMostPopularAdapter(BaseSourceAdapter[NYTimesArticle]):
    source_name = "nytimes"
    api_base_url = "https://api.nytimes.com/svc/mostpopular/v2"
    period_days = 30
    request_timeout_seconds = 10

    def __init__(
        self,
        session: requests.Session | None = None,
        api_key: str | None = None,
    ) -> None:
        self.session = session or requests.Session()
        self.api_key = api_key if api_key is not None else os.environ.get("NYTIMES_API_KEY")

    @classmethod
    def get_source_name(cls) -> str:
        return cls.source_name

    def fetch(self, category: Category, *, limit: int = 50) -> list[NYTimesArticle]:
        if not self.api_key:
            raise RuntimeError("NYTIMES_API_KEY is required for NYTimes ingestion")

        response = self.session.get(
            f"{self.api_base_url}/viewed/{self.period_days}.json",
            params={"api-key": self.api_key},
            timeout=self.request_timeout_seconds,
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        payload = cast(object, response.json())

        if not isinstance(payload, dict):
            raise ValueError("NYTimes most popular response was not an object")

        raw_results = payload.get("results")
        if not isinstance(raw_results, list):
            raise ValueError("NYTimes most popular response did not include a results list")

        articles: list[NYTimesArticle] = []
        for item in raw_results:
            if not isinstance(item, dict):
                continue
            article = self._parse_article(cast(dict[str, Any], item))
            if article is not None:
                articles.append(article)

        return articles[:limit]

    def normalise(
        self,
        raw_item: NYTimesArticle,
        category: Category,
        *,
        rank: int,
    ) -> NormalizedTrendItem:
        return NormalizedTrendItem(
            title=raw_item["title"],
            url=raw_item["url"],
            external_url=raw_item["url"],
            score=max(0, 100 - rank),
            score_label="most viewed",
            rank=rank,
        )

    def _parse_article(self, raw_item: dict[str, Any]) -> NYTimesArticle | None:
        article_id = raw_item.get("id")
        title = raw_item.get("title")
        url = raw_item.get("url")

        if not isinstance(article_id, int):
            return None
        if not isinstance(title, str) or not title.strip():
            return None
        if not isinstance(url, str) or not url.strip():
            return None

        article = NYTimesArticle(
            id=article_id,
            title=title.strip(),
            url=url.strip(),
        )

        abstract = raw_item.get("abstract")
        if isinstance(abstract, str) and abstract.strip():
            article["abstract"] = abstract.strip()

        published_date = raw_item.get("published_date")
        if isinstance(published_date, str) and published_date.strip():
            article["published_date"] = published_date.strip()

        return article
