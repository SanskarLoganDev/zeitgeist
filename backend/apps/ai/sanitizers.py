"""Text cleanup helpers for AI-generated content."""
from __future__ import annotations

import re

DEGENERATE_TOKEN_RE = re.compile(r"\b[\w.-]*(?:_0){8,}[\w.-]*\b")


def sanitize_category_summary(text: str) -> str:
    """Remove known malformed generation artifacts from category summaries."""
    without_degenerate_tokens = DEGENERATE_TOKEN_RE.sub("", text)
    return re.sub(r"[ \t]{2,}", " ", without_degenerate_tokens).strip()
