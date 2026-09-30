"""Small deterministic helpers shared by the additive architecture."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Iterable


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def utc_now() -> datetime:
    return datetime.now(UTC)


def mean(values: Iterable[float]) -> float:
    items = list(values)
    return sum(items) / len(items) if items else 0.0

