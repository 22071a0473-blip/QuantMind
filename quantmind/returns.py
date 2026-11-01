"""Shared benchmark-relative forward-return calculations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .ledger_store import LedgerStore
from .storage import MarketBarRecord


@dataclass(frozen=True, slots=True)
class ForwardReturn:
    start_date: date
    end_date: date
    raw_return: float
    benchmark_return: float
    abnormal_return: float
    path: tuple[float, ...]


def forward_abnormal_return(
    ticker: str,
    start_date: date,
    horizon_trading_days: int,
    *,
    database: Path = Path("data/quantmind.db"),
) -> ForwardReturn | None:
    """Measure from the start-date close to the h-th later trading close."""

    if horizon_trading_days <= 0:
        raise ValueError("horizon_trading_days must be positive")
    store = LedgerStore(database)
    try:
        target = sorted(store.market_bars(ticker), key=lambda bar: bar.observed_at.date())
        benchmark = {bar.observed_at.date(): bar for bar in store.market_bars("SPY")}
    finally:
        store.close()
    target_by_date = {bar.observed_at.date(): bar for bar in target}
    dates = sorted(target_by_date)
    if start_date not in target_by_date:
        return None
    start_index = dates.index(start_date)
    end_index = start_index + horizon_trading_days
    if end_index >= len(dates):
        return None
    end_date = dates[end_index]
    start_target = _price(target_by_date[start_date])
    end_target = _price(target_by_date[end_date])
    start_benchmark = benchmark.get(start_date)
    end_benchmark = benchmark.get(end_date)
    if start_benchmark is None or end_benchmark is None:
        return None
    raw_return = _percentage(end_target, start_target)
    benchmark_return = _percentage(_price(end_benchmark), _price(start_benchmark))
    path = tuple(
        _percentage(_price(target_by_date[date_value]), start_target)
        - _percentage(_price(benchmark[date_value]), _price(start_benchmark))
        for date_value in dates[start_index : end_index + 1]
        if date_value in benchmark
    )
    return ForwardReturn(
        start_date=start_date,
        end_date=end_date,
        raw_return=raw_return,
        benchmark_return=benchmark_return,
        abnormal_return=raw_return - benchmark_return,
        path=path,
    )


def _price(bar: MarketBarRecord) -> float:
    return float(bar.adjusted_close if bar.adjusted_close is not None else bar.close)


def _percentage(end: float, start: float) -> float:
    if start == 0:
        raise ValueError("price cannot be zero")
    return (end / start - 1.0) * 100.0
