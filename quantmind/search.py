"""Deterministic query understanding for the research workspace."""

from __future__ import annotations

import re
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from .universe import UNIVERSE

QueryIntent = Literal[
    "entity_lookup",
    "market_metric",
    "financial_statement",
    "event_search",
    "historical_analogue",
    "broad_research",
    "memory_recall",
]


class ParsedQuery(BaseModel):
    query: str
    intent: QueryIntent
    symbols: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    date_from: date | None = None
    date_to: date | None = None
    retrieval_strategy: list[str] = Field(default_factory=list)
    clarification: str | None = None


class SearchResult(BaseModel):
    result_id: str
    title: str
    snippet: str
    source_type: str
    source_url: str | None = None
    ticker: str | None = None
    score: float
    available_at: date | None = None


class SearchExecution(BaseModel):
    query: str
    parsed: ParsedQuery
    results: list[SearchResult] = Field(default_factory=list)
    lexical_count: int = 0
    memory_count: int = 0
    memory_status: Literal["verified", "unavailable", "not_configured"] = "not_configured"
    warnings: list[str] = Field(default_factory=list)


_METRICS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("return", ("return", "performance", "gain", "loss")),
    ("drawdown", ("drawdown", "peak to trough")),
    ("volatility", ("volatility", "risk", "standard deviation")),
    ("volume", ("volume", "turnover")),
    ("revenue", ("revenue", "sales")),
    ("margin", ("margin", "profitability")),
    ("leverage", ("leverage", "debt", "liabilities")),
)
_QUERY_STOPWORDS = {"a", "an", "and", "for", "in", "of", "on", "the", "to", "we"}


def parse_query(query: str) -> ParsedQuery:
    normalized = re.sub(r"\s+", " ", query.strip())
    lowered = normalized.casefold()
    tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9:._-]*", normalized)
    symbols = sorted(
        {
            asset.symbol
            for asset in UNIVERSE
            if any(
                token.casefold() == asset.symbol.casefold()
                and token.casefold() not in _QUERY_STOPWORDS
                and (len(token) > 1 or token.isupper())
                for token in tokens
            )
        }
    )
    metrics = [name for name, aliases in _METRICS if any(alias in lowered for alias in aliases)]
    if any(term in lowered for term in ("memory", "previous research", "precedent", "what did we find")):
        intent: QueryIntent = "memory_recall"
        strategy = ["hindsight_memory", "lexical"]
    elif any(term in lowered for term in ("similar", "analogue", "analog", "same pattern")):
        intent = "historical_analogue"
        strategy = ["structured", "hindsight_memory"]
    elif any(term in lowered for term in ("filing", "earnings", "acquisition", "contract", "news", "regulatory")):
        intent = "event_search"
        strategy = ["lexical", "structured", "hindsight_memory"]
    elif metrics and any(term in lowered for term in ("revenue", "margin", "debt", "leverage")):
        intent = "financial_statement"
        strategy = ["structured", "lexical"]
    elif metrics:
        intent = "market_metric"
        strategy = ["structured"]
    elif symbols and len(normalized.split()) <= 3:
        intent = "entity_lookup"
        strategy = ["structured"]
    else:
        intent = "broad_research"
        strategy = ["structured", "lexical", "hindsight_memory"]
    clarification = None
    if not symbols and intent not in {"broad_research", "event_search", "memory_recall"}:
        clarification = "Name a ticker or company so the result can be tied to a verified security."
    return ParsedQuery(
        query=normalized,
        intent=intent,
        symbols=symbols,
        metrics=metrics,
        retrieval_strategy=strategy,
        clarification=clarification,
    )


def fts_query(query: str) -> str:
    """Build a conservative FTS query so punctuation cannot change the MATCH grammar."""
    tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]*", query.casefold())
    return " AND ".join(f'"{token}"' for token in tokens)
