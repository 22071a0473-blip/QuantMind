"""HTTP routes for explicit hypothesis-ledger writes and read-only views."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .app import enforce_rate_limit
from .forecast import analogue_forecast
from .ledger import Hypothesis, HypothesisView, create_hypothesis, view
from .ledger_store import LedgerStore

router = APIRouter()


class CommitRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=12)
    horizon_days: Literal[5, 20, 60] = 20
    as_of: str | None = None


class LedgerListResponse(BaseModel):
    items: list[Hypothesis]
    total: int
    limit: int
    cursor: str | None = None
    next_cursor: str | None = None


class CalibrationBucket(BaseModel):
    lower: float
    upper: float
    n: int
    mean_predicted: float
    realized_frequency: float


class LedgerStatsResponse(BaseModel):
    insufficient_data: bool
    n_resolved: int
    counts: dict[str, int] = Field(default_factory=dict)
    mean_brier: float | None = None
    calibration: list[CalibrationBucket] = Field(default_factory=list)


def _store() -> LedgerStore:
    return LedgerStore(Path(os.getenv("QUANTMIND_DATABASE", "data/quantmind.db")))


@router.post("/api/ledger/commit", response_model=Hypothesis)
async def commit_ledger(request: Request, body: CommitRequest) -> Hypothesis:
    enforce_rate_limit(request)
    store = _store()
    try:
        cutoff = (
            datetime.fromisoformat(body.as_of).replace(tzinfo=UTC)
            if body.as_of
            else datetime.now(UTC)
        )
        draft = analogue_forecast(body.ticker, body.horizon_days, cutoff)
        if not draft.available or draft.probability is None:
            raise HTTPException(status_code=422, detail=draft.reason or "Not enough history to forecast responsibly.")
        return create_hypothesis(
            store, ticker=body.ticker, information_cutoff=datetime.now(UTC),
            provenance="live_forward", event_type=draft.event_type, direction=draft.direction,
            horizon_days=body.horizon_days, predicted_probability=draft.probability,
            base_rate=draft.base_rate, sample_size=draft.sample_size,
            as_of=datetime.fromisoformat(body.as_of).date() if body.as_of else None,
            forecast_algo_version=draft.forecast_algo_version,
            relaxation_level=draft.relaxation_level,
            base_rate_scope=draft.base_rate_scope,
            analogue_count=draft.analogue_count,
            memory_ids_used=draft.memory_ids_used,
            hash_version=2,
        )
    finally:
        store.close()


@router.get("/api/ledger", response_model=LedgerListResponse)
async def list_ledger(
    ticker: str | None = None,
    status: str | None = None,
    provenance: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    cursor: str | None = None,
) -> LedgerListResponse:
    store = _store()
    try:
        rows = store.list_hypotheses(ticker, status, provenance, limit, cursor)
        items = [view(store, row["id"]).hypothesis for row in rows]
        next_cursor = items[-1].created_at.isoformat() if len(items) == limit else None
        return LedgerListResponse(
            items=items,
            total=store.count_hypotheses(ticker, status, provenance),
            limit=limit,
            cursor=cursor,
            next_cursor=next_cursor,
        )
    finally:
        store.close()


@router.get("/api/ledger/stats", response_model=LedgerStatsResponse)
async def ledger_stats(provenance: str = "live_forward") -> LedgerStatsResponse:
    store = _store()
    try:
        counts = {row["status"]: int(row["count"]) for row in store.stats(provenance)}
        resolved_rows = store.resolved_metrics(provenance)
        n_resolved = len(resolved_rows)
        response = LedgerStatsResponse(
            insufficient_data=n_resolved < 20, n_resolved=n_resolved, counts=counts
        )
        if n_resolved < 20:
            return response
        buckets: list[CalibrationBucket] = []
        for lower in (0.0, 0.2, 0.4, 0.6, 0.8):
            upper = lower + 0.2
            selected = [
                row for row in resolved_rows
                if lower <= row.predicted_probability < upper
                or (upper == 1.0 and row.predicted_probability <= upper)
            ]
            buckets.append(CalibrationBucket(
                lower=lower,
                upper=upper,
                n=len(selected),
                mean_predicted=sum(row.predicted_probability for row in selected) / len(selected)
                if selected else 0.0,
                realized_frequency=sum(row.outcome for row in selected) / len(selected)
                if selected else 0.0,
            ))
        response.mean_brier = sum(row.brier for row in resolved_rows) / n_resolved
        response.calibration = buckets
        return response
    finally:
        store.close()


@router.get("/api/ledger/{hypothesis_id}", response_model=HypothesisView)
async def get_ledger(hypothesis_id: UUID) -> HypothesisView:
    store = _store()
    try:
        try:
            return view(store, hypothesis_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    finally:
        store.close()
