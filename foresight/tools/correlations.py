from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

from ._base import ToolResult


@dataclass(frozen=True, slots=True)
class CorrelationToolResult(ToolResult):
    coefficient: float | None = None


def calculate_correlation(left: list[float], right: list[float]) -> CorrelationToolResult:
    if len(left) != len(right) or len(left) < 2:
        return CorrelationToolResult(
            "unavailable",
            "correlations",
            reason="equal series of at least two points required",
        )
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    numerator = sum((a - left_mean) * (b - right_mean) for a, b in zip(left, right))
    left_norm = sqrt(sum((a - left_mean) ** 2 for a in left))
    right_norm = sqrt(sum((b - right_mean) ** 2 for b in right))
    if not left_norm or not right_norm:
        return CorrelationToolResult("unavailable", "correlations", reason="constant series have no correlation")
    return CorrelationToolResult("available", "correlations", coefficient=numerator / (left_norm * right_norm))
