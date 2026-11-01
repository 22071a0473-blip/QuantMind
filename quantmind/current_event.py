"""Point-in-time detection of the event currently being analysed."""

from __future__ import annotations

import math
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean, pstdev

from .analogues import EventQuery
from .event_store import EventStore
from .ledger_store import LedgerStore


def detect_current_event(ticker: str, cutoff: datetime) -> EventQuery | None:
    """Prefer a recent source-backed event, then fall back to a price-only shock."""
    effective_cutoff = cutoff.astimezone(UTC)
    database = Path(os.getenv("QUANTMIND_DATABASE", "data/quantmind.db"))
    event_store = EventStore(database)
    ledger_store = LedgerStore(database)
    try:
        try:
            bars = [
                bar for bar in ledger_store.market_bars(ticker.upper())
                if bar.observed_at <= effective_cutoff
            ]
        except sqlite3.OperationalError as exc:
            if "no such table" in str(exc):
                return None
            raise
        trading_dates = sorted({bar.observed_at.date() for bar in bars})
        recent_dates = set(trading_dates[-3:])
        recent_events = [
            event for event in event_store.list_events(ticker=ticker, limit=500)
            if event.event_date in recent_dates
            and event.event_date < effective_cutoff.date()
            and event.available_at < effective_cutoff
        ]
        if recent_events:
            event = max(recent_events, key=lambda item: (item.available_at, item.event_id))
            return EventQuery(
                event_id=event.event_id,
                ticker=event.ticker,
                event_date=event.event_date,
                available_at=event.available_at,
                event_type=event.event_type,
                headline=event.headline,
                source_url=event.source_url,
                sector=event.sector,
                day0_abnormal_return=event.day0_abnormal_return,
                volume_ratio=event.volume_ratio,
                pre_drift_20d=event.pre_drift_20d,
                regime_spy_ret_60d=event.regime_spy_ret_60d,
                regime_spy_vol_60d=event.regime_spy_vol_60d,
                market_cap_bucket=event.market_cap_bucket,
            )
        return _price_only_event(ticker.upper(), effective_cutoff, bars)
    finally:
        event_store.close()
        ledger_store.close()


def _price_only_event(ticker: str, cutoff: datetime, bars: list[object]) -> EventQuery | None:
    if len(bars) < 121:
        return None
    latest = bars[-1]
    benchmark_store = LedgerStore(Path(os.getenv("QUANTMIND_DATABASE", "data/quantmind.db")))
    try:
        benchmark = {
            bar.observed_at.date(): bar
            for bar in benchmark_store.market_bars("SPY")
            if bar.observed_at <= cutoff
        }
    finally:
        benchmark_store.close()
    abnormal: list[float] = []
    for current, previous in zip(bars[1:], bars[:-1]):
        spy_current = benchmark.get(current.observed_at.date())
        spy_previous = benchmark.get(previous.observed_at.date())
        if not spy_current or not spy_previous:
            continue
        target_return = _return(current.adjusted_close or current.close, previous.adjusted_close or previous.close)
        spy_return = _return(
            spy_current.adjusted_close or spy_current.close,
            spy_previous.adjusted_close or spy_previous.close,
        )
        abnormal.append(target_return - spy_return)
    if len(abnormal) < 120:
        return None
    latest_abnormal = abnormal[-1]
    trailing = abnormal[-121:-1]
    sigma = pstdev(trailing)
    volume_ratio = _volume_ratio(bars)
    if sigma <= 0 or abs(latest_abnormal) < 2 * sigma or volume_ratio < 1.5:
        return None
    return EventQuery(
        ticker=ticker,
        event_date=latest.observed_at.date(),
        available_at=latest.available_at,
        event_type="price_only",
        day0_abnormal_return=latest_abnormal,
        volume_ratio=volume_ratio,
    )


def _return(current: float, previous: float) -> float:
    return current / previous - 1 if previous else math.nan


def _volume_ratio(bars: list[object]) -> float:
    latest_volume = bars[-1].volume or 0
    prior = [bar.volume for bar in bars[-21:-1] if bar.volume is not None]
    return latest_volume / mean(prior) if prior and mean(prior) else 0.0
