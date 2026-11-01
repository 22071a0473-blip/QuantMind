"""Resolve ledger hypotheses without using observations at or before their cutoff."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, date, datetime

from .ledger import Hypothesis, Resolution, get_hypothesis, mark_status
from .ledger_store import LedgerStore, ResolutionWrite


def _price(bar: object) -> float:
    value = getattr(bar, "adjusted_close")
    return value if value is not None else getattr(bar, "close")


@dataclass(frozen=True)
class ResolutionMetrics:
    outcome: int
    brier: float
    log_loss: float


def _metrics(hypothesis: Hypothesis, raw: float, benchmark: float) -> ResolutionMetrics:
    abnormal = raw - benchmark
    success = abnormal > hypothesis.threshold
    outcome = int(success if hypothesis.direction == "outperform" else not success)
    probability = min(max(hypothesis.predicted_probability, 1e-6), 1 - 1e-6)
    probability_for_outcome = probability if outcome else 1 - probability
    return ResolutionMetrics(
        outcome=outcome,
        brier=(probability - outcome) ** 2,
        log_loss=-math.log(min(max(probability_for_outcome, 1e-6), 1 - 1e-6)),
    )


def resolve_hypothesis(store: LedgerStore, hypothesis: Hypothesis, now: date | None = None) -> Resolution | None:
    """Use the first trading day strictly after the information cutoff as entry."""
    target = sorted(store.market_bars(hypothesis.ticker), key=lambda bar: bar.observed_at)
    benchmark = sorted(store.market_bars(hypothesis.benchmark), key=lambda bar: bar.observed_at)
    cutoff = hypothesis.information_cutoff
    target_after = [bar for bar in target if bar.observed_at > cutoff]
    benchmark_by_date = {bar.observed_at.date(): bar for bar in benchmark}
    if not target_after:
        mark_status(store, hypothesis.id, "censored", "missing_start_price")
        return None
    start = target_after[0]
    target_dates = [bar.observed_at.date() for bar in target_after]
    end_index = hypothesis.horizon_days
    expected_end = target_dates[end_index] if end_index < len(target_dates) else None
    current_date = now or datetime.now(UTC).date()
    if expected_end is None:
        mark_status(store, hypothesis.id, "censored", "future_end_price_not_available")
        return None
    benchmark_start = benchmark_by_date.get(start.observed_at.date())
    benchmark_end = benchmark_by_date.get(expected_end)
    target_end = next((bar for bar in target_after if bar.observed_at.date() == expected_end), None)
    if target_end is None or benchmark_start is None or benchmark_end is None:
        if expected_end > current_date:
            mark_status(store, hypothesis.id, "censored", "future_price_data_not_available")
        else:
            missing = [
                symbol
                for symbol, bar in (
                    (hypothesis.ticker, target_end),
                    (hypothesis.benchmark, benchmark_end),
                )
                if bar is None
            ]
            mark_status(store, hypothesis.id, "invalidated", f"missing_price_data:{','.join(missing)}:{expected_end}")
        return None
    raw = _price(target_end) / _price(start) - 1
    benchmark_return = _price(benchmark_end) / _price(benchmark_start) - 1
    abnormal = raw - benchmark_return
    metrics = _metrics(hypothesis, raw, benchmark_return)
    resolution = Resolution(
        hypothesis_id=hypothesis.id,
        resolved_at=datetime.now(UTC),
        realized_raw_return=raw,
        realized_benchmark_return=benchmark_return,
        realized_abnormal_return=abnormal,
        outcome=metrics.outcome,
        brier=metrics.brier,
        log_loss=metrics.log_loss,
        start_price_date=start.observed_at.date(),
        end_price_date=expected_end,
        price_source=f"{start.provider}/{benchmark_start.provider}",
    )
    with store.transaction():
        if store.get_resolution(hypothesis.id) is None:
            store.insert_resolution(
                ResolutionWrite(
                    hypothesis_id=str(resolution.hypothesis_id),
                    resolved_at=resolution.resolved_at.isoformat(),
                    realized_raw_return=resolution.realized_raw_return,
                    realized_benchmark_return=resolution.realized_benchmark_return,
                    realized_abnormal_return=resolution.realized_abnormal_return,
                    outcome=resolution.outcome,
                    brier=resolution.brier,
                    log_loss=resolution.log_loss,
                    start_price_date=resolution.start_price_date.isoformat(),
                    end_price_date=resolution.end_price_date.isoformat(),
                    price_source=resolution.price_source,
                    notes=resolution.notes,
                )
            )
        store.connection.execute(
            "UPDATE hypotheses SET status = ?, status_reason = ? WHERE id = ?",
            ("resolved", None, str(hypothesis.id)),
        )
    return resolution


def resolve_open(store: LedgerStore, ticker: str | None = None, limit: int = 100) -> list[Resolution]:
    rows = store.list_hypotheses(ticker=ticker, limit=limit)
    results: list[Resolution] = []
    for row in rows:
        hypothesis = get_hypothesis(store, row["id"])
        if hypothesis.status not in {"open", "censored"}:
            continue
        resolution = resolve_hypothesis(store, hypothesis)
        if resolution:
            results.append(resolution)
    return results
