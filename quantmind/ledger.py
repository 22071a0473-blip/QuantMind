"""Domain models and deterministic append-only hypothesis ledger operations."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .ledger_store import HypothesisWrite, LedgerStore

Provenance = Literal["live_forward", "historical_replay"]
Direction = Literal["outperform", "underperform"]
HypothesisStatus = Literal["open", "resolved", "censored", "invalidated"]


class Hypothesis(BaseModel):
    id: UUID
    ticker: str
    security_id: UUID | None
    created_at: datetime
    information_cutoff: datetime
    as_of: date | None
    provenance: Provenance
    event_type: str
    claim_text: str
    direction: Direction
    horizon_days: Literal[5, 20, 60]
    predicted_probability: float = Field(ge=0, le=1)
    benchmark: str = "SPY"
    threshold: float = 0.0
    base_rate: float | None = None
    sample_size: int | None = None
    forecast_algo_version: str
    code_version: str
    evidence_ids: list[str] = Field(default_factory=list)
    memory_ids_used: list[str] = Field(default_factory=list)
    supersedes_id: UUID | None = None
    status: HypothesisStatus = "open"
    status_reason: str | None = None
    resolve_after: date
    record_hash: str


class Resolution(BaseModel):
    hypothesis_id: UUID
    resolved_at: datetime
    realized_raw_return: float
    realized_benchmark_return: float
    realized_abnormal_return: float
    outcome: int
    brier: float
    log_loss: float
    start_price_date: date
    end_price_date: date
    price_source: str
    notes: str | None = None


class HypothesisView(BaseModel):
    hypothesis: Hypothesis
    resolution: Resolution | None = None
    verified: bool


class HypothesisOverrides(BaseModel):
    ticker: str | None = None
    information_cutoff: datetime | None = None
    provenance: Provenance | None = None
    event_type: str | None = None
    direction: Direction | None = None
    horizon_days: Literal[5, 20, 60] | None = None
    predicted_probability: float | None = Field(default=None, ge=0, le=1)
    base_rate: float | None = None
    sample_size: int | None = None
    threshold: float | None = None
    as_of: date | None = None
    evidence_ids: list[str] | None = None
    memory_ids_used: list[str] | None = None
    forecast_algo_version: str | None = None


def _code_version() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except (OSError, subprocess.SubprocessError):
        return os.getenv("QUANTMIND_CODE_VERSION", "unknown")


def _canonical_fields(hypothesis: Hypothesis) -> dict[str, object]:
    values = hypothesis.model_dump(mode="json")
    values.pop("status", None)
    values.pop("status_reason", None)
    values.pop("record_hash", None)
    return values


def compute_record_hash(hypothesis: Hypothesis) -> str:
    payload = json.dumps(_canonical_fields(hypothesis), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _row_to_hypothesis(row: object) -> Hypothesis:
    data = dict(row)
    data["id"] = UUID(data["id"])
    data["security_id"] = UUID(data["security_id"]) if data["security_id"] else None
    data["created_at"] = datetime.fromisoformat(data["created_at"])
    data["information_cutoff"] = datetime.fromisoformat(data["information_cutoff"])
    data["as_of"] = date.fromisoformat(data["as_of"]) if data["as_of"] else None
    data["resolve_after"] = date.fromisoformat(data["resolve_after"])
    data["evidence_ids"] = json.loads(data["evidence_ids"])
    data["memory_ids_used"] = json.loads(data["memory_ids_used"])
    if data["supersedes_id"]:
        data["supersedes_id"] = UUID(data["supersedes_id"])
    return Hypothesis.model_validate(data)


def _row_to_resolution(row: object) -> Resolution:
    data = dict(row)
    data["hypothesis_id"] = UUID(data["hypothesis_id"])
    data["resolved_at"] = datetime.fromisoformat(data["resolved_at"])
    data["start_price_date"] = date.fromisoformat(data["start_price_date"])
    data["end_price_date"] = date.fromisoformat(data["end_price_date"])
    return Resolution.model_validate(data)


def _weekday_after(start: date, horizon: int) -> date:
    current = start
    remaining = horizon
    while remaining:
        current += timedelta(days=1)
        if current.weekday() < 5:
            remaining -= 1
    return current


class ResolveAfter(BaseModel):
    date: date
    reason: str | None = None


def _resolve_after(store: LedgerStore, ticker: str, cutoff: datetime, horizon: int) -> ResolveAfter:
    bars = [
        bar for bar in store.market_bars(ticker)
        if bar.observed_at.date() > cutoff.date()
    ]
    dates = sorted({bar.observed_at.date() for bar in bars})
    if len(dates) >= horizon:
        return ResolveAfter(date=dates[horizon - 1])
    return ResolveAfter(date=_weekday_after(cutoff.date(), horizon), reason="approximate_calendar")


def create_hypothesis(
    store: LedgerStore,
    *,
    ticker: str,
    information_cutoff: datetime,
    provenance: Provenance,
    event_type: str,
    direction: Direction,
    horizon_days: Literal[5, 20, 60],
    predicted_probability: float,
    base_rate: float | None,
    sample_size: int | None,
    threshold: float = 0.0,
    as_of: date | None = None,
    evidence_ids: list[str] | None = None,
    memory_ids_used: list[str] | None = None,
    supersedes_id: UUID | None = None,
    forecast_algo_version: str = "baseline-v0",
) -> Hypothesis:
    cutoff = information_cutoff.astimezone(UTC)
    resolve_after = _resolve_after(store, ticker, cutoff, horizon_days)
    security_id = store.security_id(ticker)
    probability = round(predicted_probability, 8)
    claim = (
        f"{ticker.upper()} will {direction} {threshold:.2%} versus {('SPY')} "
        f"over the next {horizon_days} trading days."
    )
    hypothesis = Hypothesis(
        id=uuid4(), ticker=ticker.upper(), security_id=UUID(security_id) if security_id else None,
        created_at=datetime.now(UTC), information_cutoff=cutoff, as_of=as_of, provenance=provenance,
        event_type=event_type, claim_text=claim, direction=direction, horizon_days=horizon_days,
        predicted_probability=probability, threshold=threshold, base_rate=base_rate, sample_size=sample_size,
        forecast_algo_version=forecast_algo_version, code_version=_code_version(),
        evidence_ids=evidence_ids or [], memory_ids_used=memory_ids_used or [], supersedes_id=supersedes_id,
        status_reason=resolve_after.reason, resolve_after=resolve_after.date, record_hash="pending",
    )
    hypothesis.record_hash = compute_record_hash(hypothesis)
    values = HypothesisWrite(
        id=str(hypothesis.id),
        ticker=hypothesis.ticker,
        security_id=str(hypothesis.security_id) if hypothesis.security_id else None,
        created_at=hypothesis.created_at.isoformat(),
        information_cutoff=hypothesis.information_cutoff.isoformat(),
        as_of=hypothesis.as_of.isoformat() if hypothesis.as_of else None,
        provenance=hypothesis.provenance,
        event_type=hypothesis.event_type,
        claim_text=hypothesis.claim_text,
        direction=hypothesis.direction,
        horizon_days=hypothesis.horizon_days,
        predicted_probability=hypothesis.predicted_probability,
        benchmark=hypothesis.benchmark,
        threshold=hypothesis.threshold,
        base_rate=hypothesis.base_rate,
        sample_size=hypothesis.sample_size,
        forecast_algo_version=hypothesis.forecast_algo_version,
        code_version=hypothesis.code_version,
        evidence_ids=json.dumps(hypothesis.evidence_ids),
        memory_ids_used=json.dumps(hypothesis.memory_ids_used),
        supersedes_id=str(hypothesis.supersedes_id) if hypothesis.supersedes_id else None,
        status=hypothesis.status,
        status_reason=hypothesis.status_reason,
        resolve_after=hypothesis.resolve_after.isoformat(),
        record_hash=hypothesis.record_hash,
    )
    return _row_to_hypothesis(store.insert_hypothesis(values))


def supersede(store: LedgerStore, old_id: UUID, new_fields: HypothesisOverrides) -> Hypothesis:
    old = get_hypothesis(store, old_id)
    values = {
        "ticker": old.ticker,
        "information_cutoff": old.information_cutoff,
        "provenance": old.provenance,
        "event_type": old.event_type,
        "direction": old.direction,
        "horizon_days": old.horizon_days,
        "predicted_probability": old.predicted_probability,
        "base_rate": old.base_rate,
        "sample_size": old.sample_size,
        "threshold": old.threshold,
        "as_of": old.as_of,
        "evidence_ids": old.evidence_ids,
        "memory_ids_used": old.memory_ids_used,
        "forecast_algo_version": old.forecast_algo_version,
        "supersedes_id": old.id,
    }
    values.update(new_fields.model_dump(exclude_none=True))
    return create_hypothesis(store, **values)


def get_hypothesis(store: LedgerStore, hypothesis_id: UUID | str) -> Hypothesis:
    row = store.get_hypothesis(hypothesis_id)
    if row is None:
        raise KeyError(f"Hypothesis {hypothesis_id} was not found.")
    return _row_to_hypothesis(row)


def verify_record(store: LedgerStore, hypothesis_id: UUID | str) -> bool:
    hypothesis = get_hypothesis(store, hypothesis_id)
    return compute_record_hash(hypothesis) == hypothesis.record_hash


def mark_status(store: LedgerStore, hypothesis_id: UUID | str, status: HypothesisStatus, reason: str | None = None) -> None:
    current = get_hypothesis(store, hypothesis_id)
    valid = {"open": {"resolved", "censored", "invalidated"}, "censored": {"resolved", "invalidated"}}
    if status != current.status and status not in valid.get(current.status, set()):
        raise ValueError(f"Invalid hypothesis transition: {current.status} -> {status}.")
    store.update_status(hypothesis_id, status, reason)


def view(store: LedgerStore, hypothesis_id: UUID | str) -> HypothesisView:
    hypothesis = get_hypothesis(store, hypothesis_id)
    row = store.get_resolution(hypothesis.id)
    return HypothesisView(
        hypothesis=hypothesis,
        resolution=_row_to_resolution(row) if row else None,
        verified=verify_record(store, hypothesis.id),
    )
