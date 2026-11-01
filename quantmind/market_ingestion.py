"""Reusable market-data contracts, normalization, validation, and ingestion."""

from __future__ import annotations

import asyncio
import math
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Protocol
from uuid import UUID, uuid4

import yfinance as yf
from pydantic import BaseModel, field_validator

from .storage import (
    DataQualityIssueRecord,
    IngestionJobRecord,
    MarketBarRecord,
    SQLiteStore,
)
from .temporal import ensure_utc


class ProviderMarketRow(BaseModel):
    observed_at: datetime
    open: float
    high: float
    low: float
    close: float
    adjusted_close: float | None = None
    volume: float | None = None
    currency: str = "USD"
    available_at: datetime | None = None

    @field_validator("observed_at", "available_at", mode="before")
    @classmethod
    def normalize_timestamp(cls, value: datetime | str | None) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, str):
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return ensure_utc(value)


class MarketCheckpoint(BaseModel):
    ticker: str
    security_id: UUID
    last_completed: date
    provider: str


class MarketDataProvider(Protocol):
    name: str

    async def daily_history(
        self,
        ticker: str,
        start: date,
        end: date,
    ) -> list[ProviderMarketRow]: ...


class YFinanceMarketDataProvider:
    """Yahoo Finance adapter used for the initial real-data pipeline."""

    name = "yfinance"

    async def daily_history(self, ticker: str, start: date, end: date) -> list[ProviderMarketRow]:
        # yfinance exposes a synchronous client, so keep its blocking request
        # outside the event loop while the ingestion workflow remains async.
        return await asyncio.to_thread(self._fetch, ticker, start, end)

    @staticmethod
    def _fetch(ticker: str, start: date, end: date) -> list[ProviderMarketRow]:
        history = yf.Ticker(ticker).history(
            start=start,
            end=end + timedelta(days=1),
            auto_adjust=False,
            actions=True,
        )
        rows: list[ProviderMarketRow] = []
        for timestamp, values in history.iterrows():
            observed_at = timestamp.to_pydatetime()
            rows.append(
                ProviderMarketRow(
                    observed_at=observed_at,
                    open=float(values["Open"]),
                    high=float(values["High"]),
                    low=float(values["Low"]),
                    close=float(values["Close"]),
                    adjusted_close=float(values["Adj Close"]) if values.get("Adj Close") is not None else None,
                    volume=float(values["Volume"]) if values.get("Volume") is not None else None,
                    available_at=observed_at,
                )
            )
        return rows


@dataclass(frozen=True, slots=True)
class QualityResult:
    accepted: list[ProviderMarketRow]
    issues: list[DataQualityIssueRecord]
    duplicate_count: int


def normalize_market_rows(rows: Iterable[ProviderMarketRow]) -> list[ProviderMarketRow]:
    """Sort and normalize provider rows without inventing missing sessions."""

    normalized = [
        row.model_copy(
            update={
                "observed_at": ensure_utc(row.observed_at),
                "available_at": ensure_utc(row.available_at or row.observed_at),
            }
        )
        for row in rows
    ]
    return sorted(normalized, key=lambda row: row.observed_at)


def validate_market_rows(
    security_id: UUID,
    rows: Iterable[ProviderMarketRow],
) -> QualityResult:
    """Reject malformed bars and flag suspicious or duplicate provider records."""

    accepted: list[ProviderMarketRow] = []
    issues: list[DataQualityIssueRecord] = []
    seen: set[datetime] = set()
    duplicate_count = 0
    previous: ProviderMarketRow | None = None
    for row in normalize_market_rows(rows):
        if row.observed_at in seen:
            duplicate_count += 1
            continue
        seen.add(row.observed_at)
        if any(not math.isfinite(value) for value in (row.open, row.high, row.low, row.close)):
            issues.append(
                DataQualityIssueRecord(
                    entity_type="security",
                    entity_id=str(security_id),
                    issue_code="non_finite_price",
                    severity="error",
                    details=f"Non-finite OHLC values at {row.observed_at.isoformat()}.",
                )
            )
            continue
        if (
            min(row.open, row.high, row.low, row.close) <= 0
            or row.high < max(row.open, row.close)
            or row.low > min(row.open, row.close)
        ):
            issues.append(
                DataQualityIssueRecord(
                    entity_type="security",
                    entity_id=str(security_id),
                    issue_code="invalid_ohlc",
                    severity="error",
                    details=f"Invalid OHLC relationship at {row.observed_at.isoformat()}.",
                )
            )
            continue
        if previous is not None and row.observed_at.date() - previous.observed_at.date() > timedelta(days=7):
            issues.append(
                DataQualityIssueRecord(
                    entity_type="security",
                    entity_id=str(security_id),
                    issue_code="missing_interval",
                    severity="warning",
                    details=(
                        f"Gap from {previous.observed_at.date().isoformat()} "
                        f"to {row.observed_at.date().isoformat()}; holidays and listing gaps require review."
                    ),
                )
            )
        accepted.append(row)
        previous = row
    return QualityResult(accepted=accepted, issues=issues, duplicate_count=duplicate_count)


def to_market_bars(security_id: UUID, rows: Iterable[ProviderMarketRow], provider: str) -> list[MarketBarRecord]:
    return [
        MarketBarRecord(
            security_id=security_id,
            observed_at=row.observed_at,
            open=row.open,
            high=row.high,
            low=row.low,
            close=row.close,
            adjusted_close=row.adjusted_close,
            volume=row.volume,
            provider=provider,
            available_at=row.available_at or row.observed_at,
        )
        for row in rows
    ]


@dataclass(frozen=True, slots=True)
class MarketIngestionResult:
    job: IngestionJobRecord
    quality: QualityResult
    stored_bars: int


def checkpoint_for(
    result: MarketIngestionResult, ticker: str, security_id: UUID, provider: str
) -> MarketCheckpoint | None:
    if not result.quality.accepted:
        return None
    return MarketCheckpoint(
        ticker=ticker,
        security_id=security_id,
        last_completed=result.quality.accepted[-1].observed_at.date(),
        provider=provider,
    )


async def ingest_market_history(
    store: SQLiteStore,
    provider: MarketDataProvider,
    security_id: UUID,
    ticker: str,
    start: date,
    end: date,
    retries: int = 3,
) -> MarketIngestionResult:
    job = IngestionJobRecord(
        job_id=uuid4(),
        job_type="market_history",
        security_id=security_id,
        requested_start=start,
        requested_end=end,
        started_at=datetime.now(UTC),
        status="running",
    )
    store.save_ingestion_job(job)
    last_error: str | None = None
    rows: list[ProviderMarketRow] = []
    for attempt in range(retries + 1):
        try:
            rows = await provider.daily_history(ticker, start, end)
            job.retry_count = attempt
            break
        except Exception as exc:
            last_error = str(exc)
            job.retry_count = attempt + 1
            if attempt >= retries:
                job.status = "failed"
                job.last_error = last_error
                job.completed_at = datetime.now(UTC)
                store.save_ingestion_job(job)
                raise
            await asyncio.sleep(min(2**attempt, 8))
    quality = validate_market_rows(security_id, rows)
    for issue in quality.issues:
        store.record_quality_issue(issue)
    bars = to_market_bars(security_id, quality.accepted, provider.name)
    existing = store.count_market_bars(
        security_id,
        provider.name,
        (bar.observed_at for bar in bars),
    )
    stored = store.upsert_market_bars(bars)
    job.status = "completed"
    job.records_received = len(rows)
    job.records_inserted = stored - existing
    job.records_updated = existing
    job.records_rejected = len(rows) - len(quality.accepted)
    job.completed_at = datetime.now(UTC)
    store.save_ingestion_job(job)
    return MarketIngestionResult(job=job, quality=quality, stored_bars=stored)
