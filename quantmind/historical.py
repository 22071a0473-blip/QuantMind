"""Point-in-time features, analogue search, outcome resolution, and evaluation."""

from __future__ import annotations

import math
import statistics
from collections.abc import Iterable, Sequence
from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .storage import MarketBarRecord, SQLiteStore
from .temporal import ensure_utc

FEATURE_VERSION = "phase3-v1"
HORIZONS = (1, 5, 20, 60, 120, 252)


class HistoricalFeature(BaseModel):
    security_id: UUID
    observed_at: datetime
    feature_version: str = FEATURE_VERSION
    price_basis: str
    values: dict[str, float | None]
    missing_features: list[str] = Field(default_factory=list)
    source_bar_count: int


class AnalogueMatch(BaseModel):
    security_id: UUID
    observed_at: datetime
    similarity: float
    distance: float
    matching_features: list[str]
    differences: list[str]
    forward_returns: dict[str, float | None]


class AnalogueQuery(BaseModel):
    query_id: UUID = Field(default_factory=uuid4)
    target_security_id: UUID
    target_date: date
    cutoff: datetime
    feature_version: str = FEATURE_VERSION
    lookback_sessions: int = 252
    minimum_similarity: float = 0.0
    matches: list[AnalogueMatch] = Field(default_factory=list)
    sample_size: int = 0
    outcome_summary: dict[str, float | int | None] = Field(default_factory=dict)


class WalkForwardConfig(BaseModel):
    train_sessions: int = Field(default=252, ge=1)
    validation_sessions: int = Field(default=63, ge=0)
    test_sessions: int = Field(default=63, ge=1)
    horizon: int = Field(default=20, ge=1)
    minimum_history: int = Field(default=252, ge=1)
    feature_version: str = FEATURE_VERSION
    transaction_cost_bps: float = Field(default=0.0, ge=0)


class EvaluationPoint(BaseModel):
    security_id: UUID
    decision_date: date
    eligible_history: int
    predicted_return: float | None
    realized_return: float | None
    excluded_reason: str | None = None


class EvaluationRun(BaseModel):
    evaluation_id: UUID = Field(default_factory=uuid4)
    security_id: UUID
    config: WalkForwardConfig
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    points: list[EvaluationPoint] = Field(default_factory=list)
    metrics: dict[str, float | int | None] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)


def _price(bar: MarketBarRecord) -> float:
    return bar.adjusted_close if bar.adjusted_close is not None else bar.close


def _returns(prices: Sequence[float]) -> list[float]:
    return [(current / previous) - 1 for previous, current in zip(prices, prices[1:]) if previous > 0]


def _safe_return(prices: Sequence[float], horizon: int) -> float | None:
    if len(prices) <= horizon or prices[-horizon - 1] <= 0:
        return None
    return prices[-1] / prices[-horizon - 1] - 1


def _rolling_std(values: Sequence[float], window: int) -> float | None:
    if len(values) < window:
        return None
    return statistics.pstdev(values[-window:])


def _z_score(values: Sequence[float], window: int) -> float | None:
    if len(values) < window:
        return None
    sample = values[-window:]
    deviation = statistics.pstdev(sample)
    return None if deviation == 0 else (sample[-1] - statistics.mean(sample)) / deviation


def compute_feature_at(
    bars: Sequence[MarketBarRecord],
    target_index: int,
    price_basis: str = "adjusted_close_fallback",
) -> HistoricalFeature:
    if not bars:
        raise ValueError("At least one market bar is required.")
    ordered = sorted(bars, key=lambda bar: ensure_utc(bar.observed_at))
    target = ordered[target_index]
    prefix = ordered[: target_index + 1]
    prices = [_price(bar) for bar in prefix]
    volumes = [bar.volume for bar in prefix if bar.volume is not None]
    daily_returns = _returns(prices)
    values: dict[str, float | None] = {}
    missing: list[str] = []
    for horizon in HORIZONS:
        key = f"return_{horizon}"
        values[key] = _safe_return(prices, horizon)
        if values[key] is None:
            missing.append(key)
    for window in (20, 60, 252):
        key = f"volatility_{window}"
        values[key] = _rolling_std(daily_returns, window)
        if values[key] is None:
            missing.append(key)
    current = prices[-1]
    peak = max(prices)
    values["drawdown_historical"] = current / peak - 1 if peak > 0 else None
    for window in (20, 60):
        window_prices = prices[-window:]
        key = f"distance_ma_{window}"
        values[key] = current / statistics.mean(window_prices) - 1 if len(window_prices) == window else None
        if values[key] is None:
            missing.append(key)
    values["gap_return"] = prefix[-1].open / prefix[-2].close - 1 if len(prefix) >= 2 and prefix[-2].close > 0 else None
    values["realized_range"] = (prefix[-1].high - prefix[-1].low) / current if current > 0 else None
    values["volume_zscore_60"] = _z_score(volumes, 60)
    values["volume_change"] = (
        prefix[-1].volume / prefix[-2].volume - 1
        if len(prefix) >= 2 and prefix[-2].volume and prefix[-1].volume is not None
        else None
    )
    for name, value in values.items():
        if value is None and name not in missing:
            missing.append(name)
    return HistoricalFeature(
        security_id=target.security_id,
        observed_at=ensure_utc(target.observed_at),
        price_basis=price_basis,
        values=values,
        missing_features=sorted(missing),
        source_bar_count=len(prefix),
    )


def eligible_market_bars(
    bars: Sequence[MarketBarRecord],
    cutoff: datetime,
) -> list[MarketBarRecord]:
    normalized_cutoff = ensure_utc(cutoff)
    return [
        bar
        for bar in sorted(bars, key=lambda item: ensure_utc(item.observed_at))
        if ensure_utc(bar.available_at) <= normalized_cutoff
    ]


def compute_features(
    bars: Sequence[MarketBarRecord],
    start: date | None = None,
    end: date | None = None,
) -> list[HistoricalFeature]:
    ordered = sorted(bars, key=lambda bar: ensure_utc(bar.observed_at))
    return [
        compute_feature_at(ordered, index)
        for index, bar in enumerate(ordered)
        if (start is None or bar.observed_at.date() >= start) and (end is None or bar.observed_at.date() <= end)
    ]


def _feature_vector(feature: HistoricalFeature) -> dict[str, float]:
    return {key: value for key, value in feature.values.items() if value is not None and math.isfinite(value)}


def _distance(target: HistoricalFeature, candidate: HistoricalFeature) -> tuple[float, list[str], list[str]]:
    target_values = _feature_vector(target)
    candidate_values = _feature_vector(candidate)
    shared = sorted(set(target_values) & set(candidate_values))
    if not shared:
        return math.inf, [], sorted(set(target_values) ^ set(candidate_values))
    distances = [(target_values[name] - candidate_values[name]) ** 2 for name in shared]
    differences = [name for name in sorted(set(target_values) | set(candidate_values)) if name not in shared]
    return math.sqrt(sum(distances) / len(distances)), shared, differences


def forward_returns(bars: Sequence[MarketBarRecord], index: int) -> dict[str, float | None]:
    ordered = sorted(bars, key=lambda bar: ensure_utc(bar.observed_at))
    prices = [_price(bar) for bar in ordered]
    base = prices[index]
    return {
        f"return_{horizon}": (
            prices[index + horizon] / base - 1 if base > 0 and index + horizon < len(prices) else None
        )
        for horizon in HORIZONS
    }


def search_analogues(
    target_bars: Sequence[MarketBarRecord],
    comparable_bars: Iterable[Sequence[MarketBarRecord]],
    target_date: date,
    cutoff: datetime,
    limit: int = 10,
    minimum_similarity: float = 0.0,
) -> AnalogueQuery:
    target_all_bars = sorted(target_bars, key=lambda bar: ensure_utc(bar.observed_at))
    target_ordered = eligible_market_bars(target_all_bars, cutoff)
    target_indexes = [index for index, bar in enumerate(target_ordered) if bar.observed_at.date() == target_date]
    if not target_indexes:
        raise ValueError(f"No target bar exists for {target_date.isoformat()}.")
    target_index = target_indexes[-1]
    target_feature = compute_feature_at(target_ordered, target_index)
    matches: list[AnalogueMatch] = []
    for bars in comparable_bars:
        ordered = sorted(bars, key=lambda bar: ensure_utc(bar.observed_at))
        eligible = eligible_market_bars(ordered, cutoff)
        eligible_timestamps = {bar.observed_at for bar in eligible}
        for index, bar in enumerate(ordered):
            if bar.observed_at not in eligible_timestamps:
                continue
            if bar.security_id == target_feature.security_id and bar.observed_at == target_feature.observed_at:
                continue
            eligible_index = next(
                position
                for position, eligible_bar in enumerate(eligible)
                if eligible_bar.observed_at == bar.observed_at
            )
            candidate = compute_feature_at(eligible, eligible_index)
            distance, shared, differences = _distance(target_feature, candidate)
            if not math.isfinite(distance):
                continue
            similarity = 1 / (1 + distance)
            if similarity < minimum_similarity:
                continue
            matches.append(
                AnalogueMatch(
                    security_id=candidate.security_id,
                    observed_at=candidate.observed_at,
                    similarity=similarity,
                    distance=distance,
                    matching_features=shared,
                    differences=differences,
                    forward_returns=forward_returns(ordered, index),
                )
            )
    matches.sort(key=lambda match: (-match.similarity, match.observed_at))
    selected = matches[:limit]
    returns = [
        match.forward_returns["return_20"] for match in selected if match.forward_returns["return_20"] is not None
    ]
    summary: dict[str, float | int | None] = {
        "sample_size": len(selected),
        "mean_return_20": statistics.mean(returns) if returns else None,
        "median_return_20": statistics.median(returns) if returns else None,
        "hit_rate_20": sum(value > 0 for value in returns) / len(returns) if returns else None,
    }
    return AnalogueQuery(
        target_security_id=target_feature.security_id,
        target_date=target_date,
        cutoff=ensure_utc(cutoff),
        matches=selected,
        sample_size=len(selected),
        outcome_summary=summary,
    )


def walk_forward_evaluate(
    bars: Sequence[MarketBarRecord],
    config: WalkForwardConfig,
) -> EvaluationRun:
    ordered = sorted(bars, key=lambda bar: ensure_utc(bar.observed_at))
    points: list[EvaluationPoint] = []
    for index in range(config.minimum_history, len(ordered) - config.horizon):
        feature = compute_feature_at(ordered, index)
        history = ordered[:index]
        returns = [
            forward_returns(ordered, prior)[f"return_{config.horizon}"]
            for prior in range(max(0, index - config.train_sessions), index)
        ]
        known = [value for value in returns if value is not None]
        if not known:
            points.append(
                EvaluationPoint(
                    security_id=ordered[index].security_id,
                    decision_date=ordered[index].observed_at.date(),
                    eligible_history=len(history),
                    predicted_return=None,
                    realized_return=None,
                    excluded_reason="insufficient_outcome_history",
                )
            )
            continue
        realized = forward_returns(ordered, index)[f"return_{config.horizon}"]
        points.append(
            EvaluationPoint(
                security_id=ordered[index].security_id,
                decision_date=ordered[index].observed_at.date(),
                eligible_history=feature.source_bar_count,
                predicted_return=statistics.mean(known),
                realized_return=realized,
                excluded_reason=None if realized is not None else "insufficient_future_observation",
            )
        )
    resolved = [point for point in points if point.realized_return is not None and point.predicted_return is not None]
    errors = [point.realized_return - point.predicted_return for point in resolved]
    directional = [
        point.predicted_return * point.realized_return > 0
        for point in resolved
        if point.predicted_return != 0 and point.realized_return != 0
    ]
    metrics: dict[str, float | int | None] = {
        "sample_size": len(resolved),
        "excluded_points": len(points) - len(resolved),
        "mae": statistics.mean(abs(error) for error in errors) if errors else None,
        "rmse": math.sqrt(statistics.mean(error**2 for error in errors)) if errors else None,
        "directional_accuracy": sum(directional) / len(directional) if directional else None,
        "mean_realized_return": statistics.mean(point.realized_return for point in resolved) if resolved else None,
    }
    return EvaluationRun(
        security_id=ordered[0].security_id if ordered else uuid4(),
        config=config,
        points=points,
        metrics=metrics,
        limitations=[
            "This baseline uses expanding historical unconditional returns; it is not a calibrated forecast.",
            "Overlapping horizons are retained for transparency and are not independent observations.",
        ],
    )


def save_feature_snapshot(store: SQLiteStore, feature: HistoricalFeature) -> None:
    store.save_json_snapshot(
        snapshot_type="feature",
        snapshot_id=f"{feature.security_id}:{feature.observed_at.isoformat()}:{feature.feature_version}",
        security_id=feature.security_id,
        observed_at=feature.observed_at,
        payload=feature.model_dump_json(),
    )


def save_evaluation(store: SQLiteStore, evaluation: EvaluationRun) -> None:
    store.save_json_snapshot(
        snapshot_type="evaluation",
        snapshot_id=str(evaluation.evaluation_id),
        security_id=evaluation.security_id,
        observed_at=evaluation.started_at,
        payload=evaluation.model_dump_json(),
    )
