"""Curated research universe and deterministic asset search."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field

AssetKind = Literal["stock", "etf", "crypto"]


class UniverseAsset(BaseModel):
    symbol: str
    name: str
    kind: AssetKind
    aliases: list[str] = Field(default_factory=list)
    sector: str | None = None


class SearchResponse(BaseModel):
    query: str
    results: list[UniverseAsset]
    total: int


UNIVERSE: tuple[UniverseAsset, ...] = (
    UniverseAsset(symbol="PLTR", name="Palantir Technologies", kind="stock", aliases=["palantir"], sector="Defense AI"),
    UniverseAsset(symbol="CRWD", name="CrowdStrike", kind="stock", aliases=["crowdstrike"], sector="Cybersecurity"),
    UniverseAsset(symbol="NVDA", name="NVIDIA", kind="stock", aliases=["nvidia"], sector="Semiconductors"),
    UniverseAsset(symbol="MSFT", name="Microsoft", kind="stock", aliases=["microsoft"], sector="Software"),
    UniverseAsset(symbol="GOOGL", name="Alphabet", kind="stock", aliases=["google", "alphabet"], sector="Software"),
    UniverseAsset(symbol="TSLA", name="Tesla", kind="stock", aliases=["tesla"], sector="Automotive"),
    UniverseAsset(symbol="QQQ", name="Invesco QQQ Trust", kind="etf", aliases=["nasdaq"], sector="Broad market"),
    UniverseAsset(symbol="SPY", name="SPDR S&P 500 ETF Trust", kind="etf", aliases=["sp500", "s&p 500"], sector="Broad market"),
    UniverseAsset(symbol="CRYPTO:bitcoin", name="Bitcoin", kind="crypto", aliases=["btc", "bitcoin"], sector="Digital assets"),
    UniverseAsset(symbol="CRYPTO:ethereum", name="Ethereum", kind="crypto", aliases=["eth", "ethereum"], sector="Digital assets"),
    UniverseAsset(symbol="CRYPTO:ondo", name="Ondo", kind="crypto", aliases=["ondo", "ondo finance"], sector="Tokenized assets"),
)


def list_universe(kind: AssetKind | None = None) -> list[UniverseAsset]:
    """Return a copy so callers cannot mutate the process-wide catalog."""
    return [asset for asset in UNIVERSE if kind is None or asset.kind == kind]


def search_universe(query: str, limit: int = 20) -> SearchResponse:
    normalized = re.sub(r"\s+", " ", query.strip().lower())
    if not normalized:
        return SearchResponse(query=query, results=[], total=0)

    terms = normalized.split(" ")
    scored: list[tuple[int, UniverseAsset]] = []
    for asset in UNIVERSE:
        fields = [
            asset.symbol.lower(),
            asset.name.lower(),
            asset.kind,
            (asset.sector or "").lower(),
            *(alias.lower() for alias in asset.aliases),
        ]
        haystack = " ".join(fields)
        score = 0
        if asset.symbol.lower() == normalized or any(alias.lower() == normalized for alias in asset.aliases):
            score += 100
        if asset.symbol.lower().startswith(normalized):
            score += 50
        score += sum(10 for term in terms if term in haystack)
        if score:
            scored.append((score, asset))

    ranked = sorted(scored, key=lambda item: (-item[0], item[1].symbol))
    results = [asset for _, asset in ranked[:limit]]
    return SearchResponse(query=query, results=results, total=len(ranked))
