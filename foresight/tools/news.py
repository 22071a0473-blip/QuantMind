from __future__ import annotations

from dataclasses import dataclass

from ._base import ToolResult


@dataclass(frozen=True, slots=True)
class NewsToolResult(ToolResult):
    headline_count: int = 0


def summarize_news(headline_count: int | None) -> NewsToolResult:
    if headline_count is None:
        return NewsToolResult("unavailable", "news", reason="news provider did not return data")
    return NewsToolResult("available", "news", headline_count=max(0, headline_count))

