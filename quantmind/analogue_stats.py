"""Outcome distributions and conservative forecast statistics for analogues."""

from __future__ import annotations

import hashlib
import math
import random
from datetime import date
from statistics import mean, median

from pydantic import BaseModel

from .analogues import AnalogueMatch


class BootstrapInterval(BaseModel):
    lower: float
    upper: float


class AnalogueStatistics(BaseModel):
    n: int
    insufficient_analogues: bool
    median: float | None = None
    mean: float | None = None
    iqr: float | None = None
    hit_rate: float | None = None
    interval_90: BootstrapInterval | None = None
    forecast_probability: float | None = None
    base_rate: float | None = None
    base_rate_scope: str | None = None


def compute_statistics(
    matches: list[AnalogueMatch],
    horizon: str = "fwd_20d",
    *,
    all_event_returns: list[float] | None = None,
    seed: int = 0,
    cutoff: date | None = None,
    direction: str = "outperform",
) -> AnalogueStatistics:
    values = [
        value
        for match in matches
        if (value := getattr(match.event, horizon, None)) is not None
        and math.isfinite(value)
        and _outcome_elapsed(match, horizon, cutoff)
    ]
    n = len(values)
    if n < 5:
        return AnalogueStatistics(n=n, insufficient_analogues=True)
    ordered = sorted(values)
    q1 = _quantile(ordered, 0.25)
    q3 = _quantile(ordered, 0.75)
    hits = sum(_is_hit(value, direction) for value in values)
    elapsed_base = all_event_returns or []
    base_values = elapsed_base if len(elapsed_base) >= 15 else values
    base_rate_scope = "all_events" if len(elapsed_base) >= 15 else "analogues"
    base_rate = sum(value > 0 for value in base_values) / len(base_values)
    if direction == "underperform":
        base_rate = 1.0 - base_rate
    probability = (hits + 10 * base_rate) / (n + 10)
    return AnalogueStatistics(
        n=n,
        insufficient_analogues=False,
        median=median(values),
        mean=mean(values),
        iqr=q3 - q1,
        hit_rate=hits / n,
        interval_90=_bootstrap_interval(values, seed),
        forecast_probability=probability,
        base_rate=base_rate,
        base_rate_scope=base_rate_scope,
    )


def _quantile(values: list[float], probability: float) -> float:
    position = (len(values) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return values[lower]
    fraction = position - lower
    return values[lower] + (values[upper] - values[lower]) * fraction


def _bootstrap_interval(values: list[float], seed: int) -> BootstrapInterval:
    rng = random.Random(seed)
    samples = [median([values[rng.randrange(len(values))] for _ in values]) for _ in range(1000)]
    samples.sort()
    return BootstrapInterval(lower=samples[49], upper=samples[949])


def stable_seed(event_id: str, horizon: str, cutoff: date | None) -> int:
    payload = f"{event_id}|{horizon}|{cutoff.isoformat() if cutoff else 'none'}"
    digest = hashlib.sha256(payload.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def _outcome_elapsed(match: AnalogueMatch, horizon: str, cutoff: date | None) -> bool:
    if cutoff is None:
        return True
    end_date = getattr(match.event, f"{horizon}_end", None)
    return end_date is not None and end_date < cutoff


def _is_hit(value: float, direction: str) -> bool:
    return value > 0 if direction == "outperform" else value <= 0
