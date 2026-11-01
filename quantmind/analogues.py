"""Deterministic feature similarity and relaxation for market-event analogues."""

from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import date, datetime

from pydantic import BaseModel, Field

from .event_store import MarketEvent
from .taxonomy import EventType

FEATURE_WEIGHTS = {
    "event_type": 0.30,
    "day0_abnormal_return": 0.20,
    "volume_ratio": 0.15,
    "sector": 0.10,
    "pre_drift_20d": 0.10,
    "regime": 0.10,
    "market_cap_bucket": 0.05,
}


class EventQuery(BaseModel):
    event_id: str | None = None
    ticker: str
    event_date: date
    available_at: datetime
    event_type: EventType
    headline: str | None = None
    source_url: str | None = None
    sector: str | None = None
    day0_abnormal_return: float | None = None
    volume_ratio: float | None = None
    pre_drift_20d: float | None = None
    regime_spy_ret_60d: float | None = None
    regime_spy_vol_60d: float | None = None
    market_cap_bucket: str | None = None


class FeatureScores(BaseModel):
    event_type: float | None = None
    day0_abnormal_return: float | None = None
    volume_ratio: float | None = None
    sector: float | None = None
    pre_drift_20d: float | None = None
    regime: float | None = None
    market_cap_bucket: float | None = None


class AnalogueMatch(BaseModel):
    event: MarketEvent
    similarity: float
    feature_scores: FeatureScores
    retrieval_source: str = "structured"
    relaxation_level: str = "L0"


class AnalogueRetrievalResult(BaseModel):
    matches: list[AnalogueMatch] = Field(default_factory=list)
    relaxation_level: str
    insufficient_analogues: bool = False
    semantic_status: str = "not_requested"
    semantic_reason: str | None = None


def _bucket(value: float | None, bounds: Sequence[float]) -> int | None:
    if value is None or not math.isfinite(value):
        return None
    for index, bound in enumerate(bounds):
        if value < bound:
            return index
    return len(bounds)


def _bucket_score(left: float | None, right: float | None, bounds: Sequence[float]) -> float | None:
    left_bucket = _bucket(left, bounds)
    right_bucket = _bucket(right, bounds)
    if left_bucket is None or right_bucket is None:
        return None
    distance = abs(left_bucket - right_bucket)
    return 1.0 if distance == 0 else 0.5 if distance == 1 else 0.0


def _tercile(value: float | None, distribution: Sequence[float]) -> int | None:
    if value is None or not distribution:
        return None
    ordered = sorted(distribution)
    first = ordered[len(ordered) // 3]
    second = ordered[(len(ordered) * 2) // 3]
    return 0 if value <= first else 1 if value <= second else 2


def feature_scores(query: EventQuery, event: MarketEvent, corpus: Sequence[MarketEvent]) -> FeatureScores:
    market_cap_score = None
    if query.market_cap_bucket is not None and event.market_cap_bucket is not None:
        market_cap_score = 1.0 if query.market_cap_bucket == event.market_cap_bucket else 0.0
    scores: dict[str, float | None] = {
        "event_type": 1.0 if query.event_type == event.event_type else 0.0,
        "day0_abnormal_return": _bucket_score(
            query.day0_abnormal_return, event.day0_abnormal_return, (-0.05, -0.02, 0.02, 0.05)
        ),
        "volume_ratio": _bucket_score(query.volume_ratio, event.volume_ratio, (1.2, 2.0, 4.0)),
        "sector": 1.0 if query.sector and query.sector == event.sector else 0.0,
        "pre_drift_20d": _tercile_match(
            query.pre_drift_20d,
            event.pre_drift_20d,
            [item.pre_drift_20d for item in corpus if item.pre_drift_20d is not None],
        ),
        "regime": None,
        "market_cap_bucket": market_cap_score,
    }
    query_regime = (
        _tercile(
            query.regime_spy_ret_60d,
            [item.regime_spy_ret_60d for item in corpus if item.regime_spy_ret_60d is not None],
        ),
        _tercile(
            query.regime_spy_vol_60d,
            [item.regime_spy_vol_60d for item in corpus if item.regime_spy_vol_60d is not None],
        ),
    )
    event_regime = (
        _tercile(
            event.regime_spy_ret_60d,
            [item.regime_spy_ret_60d for item in corpus if item.regime_spy_ret_60d is not None],
        ),
        _tercile(
            event.regime_spy_vol_60d,
            [item.regime_spy_vol_60d for item in corpus if item.regime_spy_vol_60d is not None],
        ),
    )
    if (
        query_regime[0] is not None
        and query_regime[1] is not None
        and event_regime[0] is not None
        and event_regime[1] is not None
    ):
        scores["regime"] = (
            1.0
            if query_regime == event_regime
            else 0.5
            if query_regime[0] == event_regime[0] or query_regime[1] == event_regime[1]
            else 0.0
        )
    elif query_regime[0] is not None and event_regime[0] is not None:
        scores["regime"] = 1.0 if query_regime[0] == event_regime[0] else 0.0
    return FeatureScores(**scores)


def similarity(query: EventQuery, event: MarketEvent, corpus: Sequence[MarketEvent]) -> float:
    scores = feature_scores(query, event, corpus)
    score_values = scores.model_dump(exclude_none=True)
    weight = sum(FEATURE_WEIGHTS[key] for key in score_values)
    return sum(FEATURE_WEIGHTS[key] * value for key, value in score_values.items()) / weight if weight else 0.0


def _eligible(query: EventQuery, event: MarketEvent, cutoff: datetime) -> bool:
    return event.event_id != query.event_id and event.event_date < cutoff.date() and event.available_at < cutoff


def retrieve_analogues(
    query: EventQuery,
    corpus: Sequence[MarketEvent],
    cutoff: datetime,
    limit: int = 20,
    semantic_events: Sequence[MarketEvent] | None = None,
) -> AnalogueRetrievalResult:
    eligible = [event for event in corpus if _eligible(query, event, cutoff)]
    levels = (
        ("L0", lambda event: event.event_type == query.event_type and event.sector == query.sector),
        ("L1", lambda event: event.event_type == query.event_type),
        ("L2", lambda event: _same_group(query.event_type, event.event_type)),
    )
    selected: list[AnalogueMatch] = []
    selected_level = "L2"
    for level, predicate in levels:
        candidates = [event for event in eligible if predicate(event)]
        matches = [
            AnalogueMatch(
                event=event,
                similarity=similarity(query, event, corpus),
                feature_scores=feature_scores(query, event, corpus),
                relaxation_level=level,
            )
            for event in candidates
        ]
        matches = [match for match in matches if match.similarity >= 0.5]
        if len(matches) >= 8 or level == "L2":
            selected = matches
            selected_level = level
            break
    by_id = {match.event.event_id: match for match in selected}
    for event in semantic_events or []:
        if not _eligible(query, event, cutoff):
            continue
        score = similarity(query, event, corpus)
        if score < 0.5:
            continue
        if event.event_id in by_id:
            by_id[event.event_id].retrieval_source = "both"
        else:
            by_id[event.event_id] = AnalogueMatch(
                event=event,
                similarity=score,
                feature_scores=feature_scores(query, event, corpus),
                retrieval_source="semantic",
                relaxation_level=selected_level,
            )
    selected = list(by_id.values())
    selected.sort(key=lambda match: (-match.similarity, -match.event.event_date.toordinal(), match.event.event_id))
    bounded = selected[:limit]
    return AnalogueRetrievalResult(
        matches=bounded,
        relaxation_level=selected_level,
        insufficient_analogues=len(bounded) < 5,
    )


def _same_group(left: EventType, right: EventType) -> bool:
    groups = {
        "earnings": {"earnings", "earnings_beat", "earnings_miss", "guidance_raise", "guidance_cut"},
        "corporate": {
            "contract_win",
            "major_partnership_deal",
            "m_and_a",
            "material_agreement",
            "merger_acquisition",
        },
        "people": {"leadership_change", "board_change", "layoffs_restructuring", "restructuring_layoffs"},
        "risk": {"cyber_incident", "regulatory_legal"},
        "price": {"price_move", "price_only"},
    }
    return any(left in members and right in members for members in groups.values())


def _tercile_match(query: float | None, event: float | None, distribution: Sequence[float]) -> float | None:
    query_bucket = _tercile(query, distribution)
    event_bucket = _tercile(event, distribution)
    if query_bucket is None or event_bucket is None:
        return None
    distance = abs(query_bucket - event_bucket)
    return 1.0 if distance == 0 else 0.5 if distance == 1 else 0.0
