"""Structured, provenance-aware storage for historical market events."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import UUID

from pydantic import BaseModel, Field

from .taxonomy import EventType


class MarketEvent(BaseModel):
    event_id: str
    ticker: str
    security_id: UUID | None = None
    sector: str | None = None
    event_date: date
    available_at: datetime
    event_type: EventType
    headline: str
    source_url: str
    source_kind: str
    day0_return: float | None = None
    day0_abnormal_return: float | None = None
    volume_ratio: float | None = None
    pre_drift_20d: float | None = None
    regime_spy_ret_60d: float | None = None
    regime_spy_vol_60d: float | None = None
    market_cap_bucket: str | None = None
    fwd_1d: float | None = None
    fwd_5d: float | None = None
    fwd_20d: float | None = None
    fwd_60d: float | None = None
    fwd_1d_end: date | None = None
    fwd_5d_end: date | None = None
    fwd_20d_end: date | None = None
    fwd_60d_end: date | None = None
    hindsight_document_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


def deterministic_event_id(ticker: str, event_date: date, event_type: str, source_url: str) -> str:
    payload = f"{ticker.upper()}|{event_date.isoformat()}|{event_type}|{source_url}"
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


class EventStore:
    """Owns the event table while sharing the canonical SQLite database file."""

    def __init__(self, path: Path = Path("data/quantmind.db")) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.initialize()

    def initialize(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS market_events (
                event_id TEXT PRIMARY KEY,
                ticker TEXT NOT NULL,
                security_id TEXT,
                sector TEXT,
                event_date TEXT NOT NULL,
                available_at TEXT NOT NULL,
                event_type TEXT NOT NULL,
                headline TEXT NOT NULL,
                source_url TEXT NOT NULL,
                source_kind TEXT NOT NULL,
                day0_return REAL,
                day0_abnormal_return REAL,
                volume_ratio REAL,
                pre_drift_20d REAL,
                regime_spy_ret_60d REAL,
                regime_spy_vol_60d REAL,
                market_cap_bucket TEXT,
                fwd_1d REAL,
                fwd_5d REAL,
                fwd_20d REAL,
                fwd_60d REAL,
                fwd_1d_end TEXT,
                fwd_5d_end TEXT,
                fwd_20d_end TEXT,
                fwd_60d_end TEXT,
                hindsight_document_id TEXT,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_market_events_lookup
                ON market_events(ticker, event_date, event_type);
            CREATE INDEX IF NOT EXISTS idx_market_events_available
                ON market_events(available_at, event_date);
            """
        )
        columns = {row["name"] for row in self.connection.execute("PRAGMA table_info(market_events)").fetchall()}
        for column in ("fwd_1d_end", "fwd_5d_end", "fwd_20d_end", "fwd_60d_end"):
            if column not in columns:
                self.connection.execute(f"ALTER TABLE market_events ADD COLUMN {column} TEXT")
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def upsert(self, event: MarketEvent) -> MarketEvent:
        self.connection.execute(
            """
            INSERT INTO market_events(
                event_id, ticker, security_id, sector, event_date, available_at,
                event_type, headline, source_url, source_kind, day0_return,
                day0_abnormal_return, volume_ratio, pre_drift_20d,
                regime_spy_ret_60d, regime_spy_vol_60d, market_cap_bucket,
                fwd_1d, fwd_5d, fwd_20d, fwd_60d, fwd_1d_end, fwd_5d_end,
                fwd_20d_end, fwd_60d_end, hindsight_document_id, created_at
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?
            )
            ON CONFLICT(event_id) DO UPDATE SET
                security_id=excluded.security_id,
                headline=excluded.headline,
                source_url=excluded.source_url,
                source_kind=excluded.source_kind,
                day0_return=excluded.day0_return,
                day0_abnormal_return=excluded.day0_abnormal_return,
                volume_ratio=excluded.volume_ratio,
                pre_drift_20d=excluded.pre_drift_20d,
                regime_spy_ret_60d=excluded.regime_spy_ret_60d,
                regime_spy_vol_60d=excluded.regime_spy_vol_60d,
                market_cap_bucket=excluded.market_cap_bucket,
                fwd_1d=excluded.fwd_1d,
                fwd_5d=excluded.fwd_5d,
                fwd_20d=excluded.fwd_20d,
                fwd_60d=excluded.fwd_60d,
                fwd_1d_end=excluded.fwd_1d_end,
                fwd_5d_end=excluded.fwd_5d_end,
                fwd_20d_end=excluded.fwd_20d_end,
                fwd_60d_end=excluded.fwd_60d_end,
                hindsight_document_id=excluded.hindsight_document_id
            """,
            (
                event.event_id,
                event.ticker,
                str(event.security_id) if event.security_id else None,
                event.sector,
                event.event_date.isoformat(),
                event.available_at.isoformat(),
                event.event_type,
                event.headline,
                event.source_url,
                event.source_kind,
                event.day0_return,
                event.day0_abnormal_return,
                event.volume_ratio,
                event.pre_drift_20d,
                event.regime_spy_ret_60d,
                event.regime_spy_vol_60d,
                event.market_cap_bucket,
                event.fwd_1d,
                event.fwd_5d,
                event.fwd_20d,
                event.fwd_60d,
                event.fwd_1d_end.isoformat() if event.fwd_1d_end else None,
                event.fwd_5d_end.isoformat() if event.fwd_5d_end else None,
                event.fwd_20d_end.isoformat() if event.fwd_20d_end else None,
                event.fwd_60d_end.isoformat() if event.fwd_60d_end else None,
                event.hindsight_document_id,
                event.created_at.isoformat(),
            ),
        )
        self.connection.commit()
        return self.get(event.event_id) or event

    def replace_ticker_events(self, ticker: str, events: list[MarketEvent]) -> int:
        """Replace one ticker's derived corpus so taxonomy changes cannot leave stale rows."""
        self.connection.execute("DELETE FROM market_events WHERE ticker = ?", (ticker.upper(),))
        for event in events:
            self.upsert(event)
        return len(events)

    def get(self, event_id: str) -> MarketEvent | None:
        row = self.connection.execute("SELECT * FROM market_events WHERE event_id = ?", (event_id,)).fetchone()
        return _row_to_event(row) if row else None

    def get_by_hindsight_document_id(self, document_id: str) -> MarketEvent | None:
        row = self.connection.execute(
            "SELECT * FROM market_events WHERE hindsight_document_id = ?",
            (document_id,),
        ).fetchone()
        return _row_to_event(row) if row else None

    def list_events(
        self,
        ticker: str | None = None,
        cutoff: datetime | None = None,
        limit: int = 500,
    ) -> list[MarketEvent]:
        clauses = []
        params: list[object] = []
        if ticker:
            clauses.append("ticker = ?")
            params.append(ticker.upper())
        if cutoff:
            clauses.append("event_date < ? AND available_at < ?")
            params.extend([cutoff.date().isoformat(), cutoff.astimezone(UTC).isoformat()])
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.connection.execute(
            f"SELECT * FROM market_events {where} ORDER BY event_date DESC, event_id LIMIT ?",
            [*params, limit],
        ).fetchall()
        return [_row_to_event(row) for row in rows]

    def all_events(self) -> list[MarketEvent]:
        rows = self.connection.execute("SELECT * FROM market_events ORDER BY event_id").fetchall()
        return [_row_to_event(row) for row in rows]

    def import_jsonl(self, path: Path) -> int:
        imported = 0
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            self.upsert(MarketEvent.model_validate(json.loads(line)))
            imported += 1
        return imported


def _row_to_event(row: sqlite3.Row) -> MarketEvent:
    values = dict(row)
    values["security_id"] = UUID(values["security_id"]) if values["security_id"] else None
    values["event_date"] = date.fromisoformat(values["event_date"])
    values["available_at"] = datetime.fromisoformat(values["available_at"])
    values["created_at"] = datetime.fromisoformat(values["created_at"])
    for column in ("fwd_1d_end", "fwd_5d_end", "fwd_20d_end", "fwd_60d_end"):
        values[column] = date.fromisoformat(values[column]) if values[column] else None
    return MarketEvent.model_validate(values)
