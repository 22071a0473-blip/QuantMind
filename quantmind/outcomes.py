"""Deterministic forecast outcome resolution with explicit censoring states."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel

from .historical import _price
from .storage import ForecastRecord, MarketBarRecord, OutcomeRecord, SQLiteStore
from .temporal import ensure_utc


class OutcomeResolution(BaseModel):
    forecast_id: UUID
    status: str
    realized_return: float | None = None
    observed_at: datetime | None = None
    reason: str | None = None


def resolve_forecast(
    forecast: ForecastRecord,
    bars: list[MarketBarRecord],
) -> OutcomeResolution:
    ordered = sorted(bars, key=lambda bar: ensure_utc(bar.observed_at))
    decision_bars = [
        bar for bar in ordered
        if ensure_utc(bar.observed_at) >= ensure_utc(forecast.created_at)
    ]
    if not decision_bars:
        return OutcomeResolution(
            forecast_id=forecast.forecast_id,
            status="unresolved",
            reason="no_observation_at_or_after_decision_time",
        )
    base = _price(decision_bars[0])
    horizon_index = forecast.horizon_days
    horizon_bar = decision_bars[horizon_index] if horizon_index < len(decision_bars) else None
    if horizon_bar is None:
        return OutcomeResolution(
            forecast_id=forecast.forecast_id,
            status="censored",
            reason="future_observation_not_available",
        )
    if base <= 0:
        return OutcomeResolution(
            forecast_id=forecast.forecast_id,
            status="invalidated",
            reason="non_positive_base_price",
        )
    return OutcomeResolution(
        forecast_id=forecast.forecast_id,
        status="resolved",
        realized_return=_price(horizon_bar) / base - 1,
        observed_at=ensure_utc(horizon_bar.observed_at),
    )


def persist_resolution(store: SQLiteStore, resolution: OutcomeResolution) -> None:
    store.resolve_outcome(
        OutcomeRecord(
            forecast_id=resolution.forecast_id,
            observed_at=resolution.observed_at,
            realized_return=resolution.realized_return,
            resolved_at=datetime.now(UTC),
            evaluation_status=resolution.status,
        )
    )
