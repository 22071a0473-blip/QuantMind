"""SQLite persistence for the append-only hypothesis ledger."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Iterator
from uuid import UUID

from .storage import MarketBarRecord


@dataclass(frozen=True)
class HypothesisWrite:
    id: str
    ticker: str
    security_id: str | None
    created_at: str
    information_cutoff: str
    as_of: str | None
    provenance: str
    event_type: str
    claim_text: str
    direction: str
    horizon_days: int
    predicted_probability: float
    benchmark: str
    threshold: float
    base_rate: float | None
    sample_size: int | None
    forecast_algo_version: str
    code_version: str
    evidence_ids: str
    memory_ids_used: str
    supersedes_id: str | None
    status: str
    status_reason: str | None
    resolve_after: str
    record_hash: str


@dataclass(frozen=True)
class ResolutionWrite:
    hypothesis_id: str
    resolved_at: str
    realized_raw_return: float
    realized_benchmark_return: float
    realized_abnormal_return: float
    outcome: int
    brier: float
    log_loss: float
    start_price_date: str
    end_price_date: str
    price_source: str
    notes: str | None


@dataclass(frozen=True)
class ResolvedMetric:
    predicted_probability: float
    outcome: int
    brier: float


def _iso(value: datetime | date | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


class LedgerStore:
    def __init__(self, path: Path = Path("data/quantmind.db")) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.initialize()

    def initialize(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS hypotheses (
                id TEXT PRIMARY KEY,
                ticker TEXT NOT NULL,
                security_id TEXT,
                created_at TEXT NOT NULL,
                information_cutoff TEXT NOT NULL,
                as_of TEXT,
                provenance TEXT NOT NULL CHECK(provenance IN ('live_forward', 'historical_replay')),
                event_type TEXT NOT NULL,
                claim_text TEXT NOT NULL,
                direction TEXT NOT NULL CHECK(direction IN ('outperform', 'underperform')),
                horizon_days INTEGER NOT NULL CHECK(horizon_days IN (5, 20, 60)),
                predicted_probability REAL NOT NULL CHECK(predicted_probability BETWEEN 0 AND 1),
                benchmark TEXT NOT NULL DEFAULT 'SPY',
                threshold REAL NOT NULL DEFAULT 0.0,
                base_rate REAL,
                sample_size INTEGER,
                forecast_algo_version TEXT NOT NULL,
                code_version TEXT NOT NULL,
                evidence_ids TEXT NOT NULL,
                memory_ids_used TEXT NOT NULL,
                supersedes_id TEXT REFERENCES hypotheses(id),
                status TEXT NOT NULL DEFAULT 'open'
                    CHECK(status IN ('open', 'resolved', 'censored', 'invalidated')),
                status_reason TEXT,
                resolve_after TEXT NOT NULL,
                record_hash TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS resolutions (
                hypothesis_id TEXT PRIMARY KEY REFERENCES hypotheses(id),
                resolved_at TEXT NOT NULL,
                realized_raw_return REAL NOT NULL,
                realized_benchmark_return REAL NOT NULL,
                realized_abnormal_return REAL NOT NULL,
                outcome INTEGER NOT NULL,
                brier REAL NOT NULL,
                log_loss REAL NOT NULL,
                start_price_date TEXT NOT NULL,
                end_price_date TEXT NOT NULL,
                price_source TEXT NOT NULL,
                notes TEXT
            );
            DROP INDEX IF EXISTS idx_hypothesis_dedup;
            CREATE UNIQUE INDEX IF NOT EXISTS idx_hypothesis_dedup ON hypotheses(
                ticker, provenance, COALESCE(as_of, substr(created_at, 1, 10)),
                event_type, horizon_days, direction, forecast_algo_version,
                COALESCE(supersedes_id, '')
            );
            CREATE TRIGGER IF NOT EXISTS hypotheses_immutable_update
            BEFORE UPDATE ON hypotheses
            WHEN OLD.id != NEW.id OR OLD.ticker != NEW.ticker OR
                 OLD.security_id IS NOT NEW.security_id OR OLD.created_at != NEW.created_at OR
                 OLD.information_cutoff != NEW.information_cutoff OR OLD.as_of IS NOT NEW.as_of OR
                 OLD.provenance != NEW.provenance OR OLD.event_type != NEW.event_type OR
                 OLD.claim_text != NEW.claim_text OR OLD.direction != NEW.direction OR
                 OLD.horizon_days != NEW.horizon_days OR
                 OLD.predicted_probability != NEW.predicted_probability OR
                 OLD.benchmark != NEW.benchmark OR OLD.threshold != NEW.threshold OR
                 OLD.base_rate IS NOT NEW.base_rate OR OLD.sample_size IS NOT NEW.sample_size OR
                 OLD.forecast_algo_version != NEW.forecast_algo_version OR
                 OLD.code_version != NEW.code_version OR OLD.evidence_ids != NEW.evidence_ids OR
                 OLD.memory_ids_used != NEW.memory_ids_used OR
                 OLD.supersedes_id IS NOT NEW.supersedes_id OR OLD.resolve_after != NEW.resolve_after OR
                 OLD.record_hash != NEW.record_hash
            BEGIN SELECT RAISE(ABORT, 'hypotheses are append-only'); END;
            CREATE TRIGGER IF NOT EXISTS hypotheses_no_delete
            BEFORE DELETE ON hypotheses
            BEGIN SELECT RAISE(ABORT, 'hypotheses are append-only'); END;
            CREATE TRIGGER IF NOT EXISTS resolutions_no_update
            BEFORE UPDATE ON resolutions
            BEGIN SELECT RAISE(ABORT, 'resolutions are immutable'); END;
            CREATE TRIGGER IF NOT EXISTS resolutions_no_delete
            BEFORE DELETE ON resolutions
            BEGIN SELECT RAISE(ABORT, 'resolutions are immutable'); END;
            """
        )
        self.connection.commit()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        try:
            yield self.connection
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    def close(self) -> None:
        self.connection.close()

    def insert_hypothesis(self, values: HypothesisWrite) -> sqlite3.Row:
        try:
            self.connection.execute(
                """
                INSERT INTO hypotheses(
                    id, ticker, security_id, created_at, information_cutoff, as_of,
                    provenance, event_type, claim_text, direction, horizon_days,
                    predicted_probability, benchmark, threshold, base_rate, sample_size,
                    forecast_algo_version, code_version, evidence_ids, memory_ids_used,
                    supersedes_id, status, status_reason, resolve_after, record_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    values.id, values.ticker, values.security_id, values.created_at,
                    values.information_cutoff, values.as_of, values.provenance,
                    values.event_type, values.claim_text, values.direction,
                    values.horizon_days, values.predicted_probability, values.benchmark,
                    values.threshold, values.base_rate, values.sample_size,
                    values.forecast_algo_version, values.code_version, values.evidence_ids,
                    values.memory_ids_used, values.supersedes_id, values.status,
                    values.status_reason, values.resolve_after, values.record_hash,
                ),
            )
            self.connection.commit()
        except sqlite3.IntegrityError as exc:
            if "idx_hypothesis_dedup" not in str(exc) and "UNIQUE constraint" not in str(exc):
                raise
        row = self.connection.execute(
            """
            SELECT * FROM hypotheses
            WHERE ticker = ? AND provenance = ? AND
                  COALESCE(as_of, substr(created_at, 1, 10)) = COALESCE(?, substr(?, 1, 10)) AND
                  event_type = ? AND horizon_days = ? AND direction = ? AND forecast_algo_version = ?
                  AND COALESCE(supersedes_id, '') = COALESCE(?, '')
            ORDER BY created_at LIMIT 1
            """,
            (
                values.ticker, values.provenance, values.as_of, values.created_at,
                values.event_type, values.horizon_days, values.direction,
                values.forecast_algo_version, values.supersedes_id,
            ),
        ).fetchone()
        if row is None:
            raise RuntimeError("Hypothesis insert did not produce a row.")
        return row

    def get_hypothesis(self, hypothesis_id: UUID | str) -> sqlite3.Row | None:
        return self.connection.execute("SELECT * FROM hypotheses WHERE id = ?", (str(hypothesis_id),)).fetchone()

    def list_hypotheses(
        self,
        ticker: str | None = None,
        status: str | None = None,
        provenance: str | None = None,
        limit: int = 50,
        cursor: str | None = None,
    ) -> list[sqlite3.Row]:
        clauses = []
        params: list[object] = []
        for field, value in (("ticker", ticker), ("status", status), ("provenance", provenance)):
            if value:
                clauses.append(f"{field} = ?")
                params.append(value)
        if cursor:
            clauses.append("created_at < ?")
            params.append(cursor)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(limit)
        return self.connection.execute(
            f"SELECT * FROM hypotheses {where} ORDER BY created_at DESC, id DESC LIMIT ?", params
        ).fetchall()

    def count_hypotheses(
        self,
        ticker: str | None = None,
        status: str | None = None,
        provenance: str | None = None,
    ) -> int:
        clauses = []
        params: list[object] = []
        for field, value in (("ticker", ticker), ("status", status), ("provenance", provenance)):
            if value:
                clauses.append(f"{field} = ?")
                params.append(value)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        row = self.connection.execute(f"SELECT COUNT(*) AS count FROM hypotheses {where}", params).fetchone()
        return int(row["count"])

    def update_status(self, hypothesis_id: UUID | str, status: str, reason: str | None) -> None:
        self.connection.execute(
            "UPDATE hypotheses SET status = ?, status_reason = ? WHERE id = ?",
            (status, reason, str(hypothesis_id)),
        )
        self.connection.commit()

    def get_resolution(self, hypothesis_id: UUID | str) -> sqlite3.Row | None:
        return self.connection.execute(
            "SELECT * FROM resolutions WHERE hypothesis_id = ?", (str(hypothesis_id),)
        ).fetchone()

    def insert_resolution(self, values: ResolutionWrite) -> None:
        self.connection.execute(
            """
            INSERT INTO resolutions(
                hypothesis_id, resolved_at, realized_raw_return,
                realized_benchmark_return, realized_abnormal_return, outcome,
                brier, log_loss, start_price_date, end_price_date, price_source, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                values.hypothesis_id, values.resolved_at, values.realized_raw_return,
                values.realized_benchmark_return, values.realized_abnormal_return,
                values.outcome, values.brier, values.log_loss,
                values.start_price_date, values.end_price_date, values.price_source,
                values.notes,
            ),
        )

    def market_bars(self, ticker: str) -> list[MarketBarRecord]:
        rows = self.connection.execute(
            """
            SELECT b.* FROM market_bars b JOIN securities s ON s.security_id = b.security_id
            WHERE UPPER(s.ticker) = UPPER(?) ORDER BY b.observed_at, b.provider
            """,
            (ticker,),
        ).fetchall()
        return [
            MarketBarRecord(
                security_id=UUID(row["security_id"]),
                observed_at=datetime.fromisoformat(row["observed_at"]),
                open=row["open"], high=row["high"], low=row["low"], close=row["close"],
                adjusted_close=row["adjusted_close"], volume=row["volume"],
                provider=row["provider"], available_at=datetime.fromisoformat(row["available_at"]),
                ingested_at=datetime.fromisoformat(row["ingested_at"]),
            )
            for row in rows
        ]

    def security_id(self, ticker: str) -> str | None:
        row = self.connection.execute(
            "SELECT security_id FROM securities WHERE UPPER(ticker) = UPPER(?) LIMIT 1", (ticker,)
        ).fetchone()
        return str(row["security_id"]) if row else None

    def stats(self, provenance: str | None = None) -> list[sqlite3.Row]:
        clause = "WHERE provenance = ?" if provenance else ""
        params = (provenance,) if provenance else ()
        return self.connection.execute(
            f"SELECT status, COUNT(*) AS count FROM hypotheses {clause} GROUP BY status", params
        ).fetchall()

    def resolved_metrics(self, provenance: str) -> list[ResolvedMetric]:
        rows = self.connection.execute(
            """
            SELECT h.predicted_probability, r.outcome, r.brier
            FROM hypotheses h JOIN resolutions r ON r.hypothesis_id = h.id
            WHERE h.provenance = ? AND h.status = 'resolved'
            """,
            (provenance,),
        ).fetchall()
        return [
            ResolvedMetric(
                predicted_probability=float(row["predicted_probability"]),
                outcome=int(row["outcome"]),
                brier=float(row["brier"]),
            )
            for row in rows
        ]
