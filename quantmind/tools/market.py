from __future__ import annotations

from dataclasses import dataclass

from ._base import ToolResult


@dataclass(frozen=True, slots=True)
class MarketToolResult(ToolResult):
    asset: str = ""
    price: float | None = None
    change_pct: float | None = None


def calculate_market(asset: str, price: float | None, previous_price: float | None) -> MarketToolResult:
    if price is None or previous_price in (None, 0):
        return MarketToolResult("unavailable", "market", reason="price history unavailable", asset=asset)
    return MarketToolResult("available", "market", asset=asset, price=price,
                            change_pct=(price / previous_price - 1) * 100)

