"""Asset universe loading and ranked search."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field
from rapidfuzz.fuzz import WRatio

AssetKind = Literal["stock", "etf", "crypto"]
_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "universe.json"
logger = logging.getLogger(__name__)


class UniverseAsset(BaseModel):
    symbol: str
    name: str
    kind: AssetKind
    sector: str | None = None
    industry: str | None = None
    cik: str | None = None
    aliases: list[str] = Field(default_factory=list)
    in_sp100: bool = False
    memory_event_count: int = 0
    search_terms: tuple[str, ...] = ()

    def model_post_init(self, __context: object) -> None:
        if not self.search_terms:
            terms = (self.symbol, self.name, *self.aliases)
            object.__setattr__(self, "search_terms", tuple(term.casefold() for term in terms))


class SearchResponse(BaseModel):
    query: str
    results: list[UniverseAsset]
    total: int


def _load_assets() -> tuple[UniverseAsset, ...]:
    try:
        payload = json.loads(_DATA_PATH.read_text(encoding="utf-8"))
        return tuple(UniverseAsset.model_validate(item) for item in payload)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        logger.error("UNIVERSE LOAD FAILED: unable to load %s: %s", _DATA_PATH, exc)
        return ()


UNIVERSE = _load_assets()


@dataclass(frozen=True, slots=True)
class RankedAsset:
    score: int
    asset: UniverseAsset


def list_universe(kind: AssetKind | None = None) -> list[UniverseAsset]:
    return [asset for asset in UNIVERSE if kind is None or asset.kind == kind]


def search_universe(query: str, limit: int = 20) -> SearchResponse:
    normalized = re.sub(r"\s+", " ", query.strip().lower())
    if not normalized:
        return SearchResponse(query=query, results=[], total=0)
    ranked: list[RankedAsset] = []
    for asset in UNIVERSE:
        ticker = asset.symbol.casefold()
        names = asset.search_terms
        score = 0
        if ticker == normalized:
            score = 500
        elif ticker.startswith(normalized):
            score = 400
        elif any(name.startswith(normalized) for name in names):
            score = 300
        elif any(token.startswith(normalized) for name in names for token in name.split()):
            score = 200
        else:
            search_text = " ".join([asset.symbol, asset.name, asset.sector or "", asset.industry or "", *asset.aliases])
            score = int(max(0, WRatio(normalized, search_text)) / 2)
            if score < 35:
                continue
        ranked.append(RankedAsset(score, asset))
    ranked.sort(key=lambda item: (-item.score, not item.asset.in_sp100, item.asset.symbol))
    return SearchResponse(query=query, results=[item.asset for item in ranked[:limit]], total=len(ranked))
