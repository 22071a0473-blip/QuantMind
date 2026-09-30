"""Market-event records and deterministic event classification."""

from __future__ import annotations

import json
import re
from datetime import date
from typing import Literal

from pydantic import BaseModel

from .taxonomy import EventType


class EventRecord(BaseModel):
    ticker: str
    sector: str | None = None
    event_date: date
    event_type: EventType
    headline: str | None = None
    filing_url: str | None = None
    return_1d: float
    abnormal_return_1d: float | None = None
    volume_ratio: float
    close: float
    forward_return_1d: float | None = None
    forward_return_5d: float | None = None
    forward_return_20d: float | None = None
    forward_return_60d: float | None = None
    source: str = "Yahoo Finance historical prices"

    def to_memory_text(self) -> str:
        def sign(value: float | None) -> str:
            return "null" if value is None else f"{value:+.2f}%"

        headline = self.headline or f"{self.ticker} historical market event"
        url = self.filing_url or "https://finance.yahoo.com/"
        encoded_headline = "null" if self.headline is None else self.headline.replace("|", "/")
        encoded_url = "null" if self.filing_url is None else self.filing_url
        narrative = (
            f"{self.ticker} recorded a {self.event_type} event on {self.event_date.isoformat()}: "
            f"{headline}. The stock moved {sign(self.return_1d)} on {self.volume_ratio:.1f}x normal volume; "
            f"abnormal return versus the S&P 500 was {sign(self.abnormal_return_1d)}. "
            f"Forward returns were 1d {sign(self.forward_return_1d)}, 5d {sign(self.forward_return_5d)}, "
            f"20d {sign(self.forward_return_20d)}, and 60d {sign(self.forward_return_60d)}. "
            f"Source: {url} ({self.source})."
        )
        structured = (
            f"[EVENT] ticker={self.ticker} | sector={self.sector or 'unknown'} | "
            f"date={self.event_date.isoformat()} | type={self.event_type} | "
            f"headline={encoded_headline} | source={self.source} | "
            f"day0={sign(self.return_1d)} | abnormal={sign(self.abnormal_return_1d)} | "
            f"volume={self.volume_ratio:.4f} | close={self.close:.6f} | "
            f"fwd_1d={sign(self.forward_return_1d)} | fwd_5d={sign(self.forward_return_5d)} | "
            f"fwd_20d={sign(self.forward_return_20d)} | fwd_60d={sign(self.forward_return_60d)} | "
            f"url={encoded_url}"
        )
        return f"{narrative}\n\n{structured}"

    @classmethod
    def from_memory_text(cls, text: str) -> EventRecord:
        structured = re.search(r"^\[EVENT\]\s+(.+)$", text, flags=re.MULTILINE)
        if not structured:
            return cls.model_validate_json(text)
        fields = dict(
            part.split("=", 1)
            for part in structured.group(1).split(" | ")
            if "=" in part
        )

        def parse_percent(name: str) -> float | None:
            value = fields.get(name, "null").strip()
            return None if value in {"null", "not yet observable"} else float(value.rstrip("%+"))

        source_url = fields.get("url")
        return cls(
            ticker=fields["ticker"],
            sector=None if fields.get("sector") == "unknown" else fields.get("sector"),
            event_date=date.fromisoformat(fields["date"]),
            event_type=fields["type"],
            headline=None if fields.get("headline") == "null" else fields.get("headline"),
            filing_url=None if source_url == "null" else source_url,
            return_1d=parse_percent("day0") or 0.0,
            abnormal_return_1d=parse_percent("abnormal"),
            volume_ratio=float(fields.get("volume", "0")),
            close=float(fields.get("close", "0")),
            forward_return_1d=parse_percent("fwd_1d"),
            forward_return_5d=parse_percent("fwd_5d"),
            forward_return_20d=parse_percent("fwd_20d"),
            forward_return_60d=parse_percent("fwd_60d"),
            source=fields.get("source", "Yahoo Finance historical prices"),
        )


class DailyMarketRow(BaseModel):
    event_date: date
    close: float
    return_1d: float
    return_5d: float
    spy_return_1d: float | None = None
    abnormal_sigma: float | None = None
    volume_ratio: float
    high: float
    low: float


def classify_price_event(row: DailyMarketRow) -> Literal["price_move"] | None:
    abnormal_move = row.return_1d - (row.spy_return_1d or 0.0)
    if row.abnormal_sigma and abs(abnormal_move) >= 2.0 * row.abnormal_sigma:
        return "price_move"
    return None


def compute_forward_return(closes: list[float], event_index: int, horizon: int = 5) -> float | None:
    target_index = event_index + horizon
    if event_index < 0 or target_index >= len(closes) or closes[event_index] == 0:
        return None
    return (closes[target_index] / closes[event_index] - 1.0) * 100.0
