"""Validated, human-curated catalyst labels used to fill provider coverage gaps."""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from pydantic import BaseModel, HttpUrl

from .taxonomy import EventType


class CuratedEvent(BaseModel):
    ticker: str
    event_date: date
    event_type: EventType
    headline: str
    source_url: HttpUrl


def load_curated_events(path: Path = Path("data/known_events.csv")) -> list[CuratedEvent]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [
            CuratedEvent(
                ticker=row["ticker"].upper(),
                event_date=date.fromisoformat(row["date"]),
                event_type=row["type"],  # type: ignore[arg-type]
                headline=row["headline"],
                source_url=row["source_url"],
            )
            for row in csv.DictReader(handle)
        ]
