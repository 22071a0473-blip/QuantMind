"""Deterministic baseline probability forecast for the hypothesis ledger."""

from __future__ import annotations

import os
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from .analogue_retrieval import AnalogueService
from .current_event import detect_current_event
from .ledger_store import LedgerStore


class ForecastDraft(BaseModel):
    ticker: str
    available: bool
    probability: float | None = None
    base_rate: float | None = None
    sample_size: int = 0
    direction: Literal["outperform", "underperform"] = "outperform"
    event_type: str = "price_only"
    forecast_algo_version: str = "baseline-v0"
    reason: str | None = None
    relaxation_level: str | None = None
    base_rate_scope: str | None = None
    analogue_count: int = 0
    memory_ids_used: list[str] = Field(default_factory=list)


def baseline_forecast(
    ticker: str,
    as_of: date | None = None,
    *,
    store: LedgerStore | None = None,
    horizon_days: Literal[5, 20, 60] = 20,
) -> ForecastDraft:
    owned = store is None
    ledger_store = store or LedgerStore(Path(os.getenv("QUANTMIND_DATABASE", "data/quantmind.db")))
    try:
        target = ledger_store.market_bars(ticker)
        benchmark = ledger_store.market_bars("SPY")
        if as_of:
            target = [bar for bar in target if bar.observed_at.date() <= as_of]
            benchmark = [bar for bar in benchmark if bar.observed_at.date() <= as_of]
        target_by_date = {bar.observed_at.date(): bar for bar in target}
        benchmark_by_date = {bar.observed_at.date(): bar for bar in benchmark}
        dates = sorted(set(target_by_date) & set(benchmark_by_date))
        observations: list[float] = []
        for index in range(len(dates) - horizon_days):
            start = dates[index]
            end = dates[index + horizon_days]
            start_target = target_by_date[start].adjusted_close or target_by_date[start].close
            end_target = target_by_date[end].adjusted_close or target_by_date[end].close
            start_benchmark = benchmark_by_date[start].adjusted_close or benchmark_by_date[start].close
            end_benchmark = benchmark_by_date[end].adjusted_close or benchmark_by_date[end].close
            if min(start_target, end_target, start_benchmark, end_benchmark) <= 0:
                continue
            observations.append((end_target / start_target - 1) - (end_benchmark / start_benchmark - 1))
        sample_size = len(observations)
        if sample_size < 30:
            return ForecastDraft(
                ticker=ticker.upper(), available=False, sample_size=sample_size,
                reason=f"Only {sample_size} complete benchmark observations; at least 30 are required.",
            )
        probability = sum(value > 0 for value in observations) / sample_size
        return ForecastDraft(
            ticker=ticker.upper(), available=True, probability=probability,
            base_rate=probability, sample_size=sample_size,
        )
    finally:
        if owned:
            ledger_store.close()


def analogue_forecast(
    ticker: str,
    horizon_days: Literal[5, 20, 60],
    cutoff: datetime | None = None,
) -> ForecastDraft:
    effective_cutoff = cutoff or datetime.now(UTC)
    query = detect_current_event(ticker, effective_cutoff)
    if query is None:
        return ForecastDraft(
            ticker=ticker.upper(),
            available=False,
            forecast_algo_version="analogue-v1",
            reason="No qualifying event was detected before the information cutoff.",
        )
    study = AnalogueService(Path(os.getenv("QUANTMIND_DATABASE", "data/quantmind.db"))).study(
        query,
        cutoff=effective_cutoff,
    )
    statistic = study.statistics[f"fwd_{horizon_days}d"]
    if statistic.insufficient_analogues or statistic.forecast_probability is None:
        return ForecastDraft(
            ticker=ticker.upper(),
            available=False,
            event_type=query.event_type,
            forecast_algo_version="analogue-v1",
            relaxation_level=study.relaxation_level,
            base_rate_scope=statistic.base_rate_scope,
            analogue_count=statistic.n,
            memory_ids_used=[match.event.event_id for match in study.matches],
            reason=f"Only {statistic.n} elapsed analogue outcomes are available; at least 5 are required.",
        )
    return ForecastDraft(
        ticker=ticker.upper(),
        available=True,
        probability=statistic.forecast_probability,
        base_rate=statistic.base_rate,
        sample_size=statistic.n,
        event_type=query.event_type,
        forecast_algo_version="analogue-v1",
        relaxation_level=study.relaxation_level,
        base_rate_scope=statistic.base_rate_scope,
        analogue_count=statistic.n,
        memory_ids_used=[match.event.event_id for match in study.matches],
    )
