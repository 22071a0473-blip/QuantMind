"""Offline historical replay service for the Time Machine surface."""

from __future__ import annotations

import os
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal
from uuid import UUID

from fastapi import HTTPException
from pydantic import BaseModel, Field

from .analogue_retrieval import AnalogueService
from .analogue_stats import AnalogueStatistics
from .analogues import AnalogueMatch, EventQuery, FeatureScores
from .cutoff import cutoff_for_as_of
from .event_store import EventStore
from .ledger import Hypothesis, Resolution, create_hypothesis, get_hypothesis
from .ledger_store import LedgerStore
from .resolver import resolve_hypothesis


class TimeMachineCandidate(BaseModel):
    ticker: str
    as_of: date
    information_cutoff: datetime
    event_id: str
    event_type: str
    headline: str
    available_at: datetime
    history_days: int


class TimeMachineCandidatePage(BaseModel):
    items: list[TimeMachineCandidate] = Field(default_factory=list)
    total: int
    limit: int
    offset: int


class TimeMachineForecastRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=12)
    as_of: date
    horizon_days: Literal[5, 20, 60] = 20


class TimeMachineRevealRequest(BaseModel):
    hypothesis_id: UUID


class TimeMachineForwardReturns(BaseModel):
    fwd_1d: float | None = None
    fwd_5d: float | None = None
    fwd_20d: float | None = None
    fwd_60d: float | None = None


class TimeMachineMatch(BaseModel):
    event_id: str
    ticker: str
    event_date: date
    event_type: str
    headline: str
    source_url: str
    similarity: float
    feature_scores: FeatureScores
    retrieval_source: str
    relaxation_level: str
    forward_returns: TimeMachineForwardReturns


class TimeMachineForecast(BaseModel):
    ticker: str
    as_of: date
    information_cutoff: datetime
    event: EventQuery
    matches: list[TimeMachineMatch]
    distributions: dict[str, AnalogueStatistics]
    relaxation_level: str
    insufficient_analogues: bool
    hypothesis_id: UUID | None = None
    provenance: str = "historical_replay"


class TimeMachineReveal(BaseModel):
    hypothesis_id: UUID
    revealed: bool
    resolve_after: date
    status: str
    status_reason: str | None = None
    resolution: Resolution | None = None


class TimeMachineService:
    def __init__(self, database: Path | None = None) -> None:
        self.database = database or Path(os.environ.get("QUANTMIND_DATABASE", "data/quantmind.db"))

    def candidates(self, ticker: str, *, limit: int = 100, offset: int = 0) -> TimeMachineCandidatePage:
        normalized = ticker.upper()
        event_store = EventStore(self.database)
        ledger_store = LedgerStore(self.database)
        try:
            bars = ledger_store.market_bars(normalized)
            dates = sorted({bar.observed_at.date() for bar in bars})
            events = [
                event
                for event in event_store.all_events()
                if event.ticker == normalized and event.event_date in dates
            ]
            items = [
                TimeMachineCandidate(
                    ticker=normalized,
                    as_of=event.event_date,
                    information_cutoff=cutoff_for_as_of(event.event_date).information_cutoff,
                    event_id=event.event_id,
                    event_type=event.event_type,
                    headline=event.headline,
                    available_at=event.available_at,
                    history_days=sum(candidate < event.event_date for candidate in dates),
                )
                for event in events
                if event.available_at < cutoff_for_as_of(event.event_date).information_cutoff
                and sum(candidate < event.event_date for candidate in dates) >= 120
            ]
        finally:
            event_store.close()
            ledger_store.close()
        items.sort(key=lambda item: (item.as_of, item.event_id), reverse=True)
        return TimeMachineCandidatePage(items=items[offset : offset + limit], total=len(items), limit=limit, offset=offset)

    async def forecast(self, ticker: str, as_of: date, horizon_days: int) -> TimeMachineForecast:
        cutoff = cutoff_for_as_of(as_of)
        database = self.database
        ledger_store = LedgerStore(database)
        event_store = EventStore(database)
        try:
            bars = ledger_store.market_bars(ticker.upper())
            history_days = sum(bar.observed_at.date() < as_of for bar in bars)
            if history_days < 120:
                raise HTTPException(status_code=422, detail="as_of requires at least 120 prior trading days")
            event = next(
                (
                    candidate
                    for candidate in event_store.all_events()
                    if candidate.ticker == ticker.upper()
                    and candidate.event_date == as_of
                    and candidate.available_at < cutoff.information_cutoff
                ),
                None,
            )
        finally:
            ledger_store.close()
            event_store.close()
        if event is None:
            raise HTTPException(status_code=422, detail="No source-backed event is visible on the requested date")
        query = EventQuery(
            event_id=event.event_id,
            ticker=event.ticker,
            event_date=event.event_date,
            available_at=event.available_at,
            event_type=event.event_type,
            headline=event.headline,
            source_url=event.source_url,
            sector=event.sector,
            day0_abnormal_return=event.day0_abnormal_return,
            volume_ratio=event.volume_ratio,
            pre_drift_20d=event.pre_drift_20d,
            regime_spy_ret_60d=event.regime_spy_ret_60d,
            regime_spy_vol_60d=event.regime_spy_vol_60d,
            market_cap_bucket=event.market_cap_bucket,
        )
        study = AnalogueService(database).study(query, cutoff=cutoff.information_cutoff)
        statistics = study.statistics
        horizon = f"fwd_{horizon_days}d"
        selected = statistics[horizon]
        hypothesis: Hypothesis | None = None
        if not selected.insufficient_analogues and selected.forecast_probability is not None:
            direction = "outperform" if selected.forecast_probability >= 0.5 else "underperform"
            store = LedgerStore(database)
            try:
                hypothesis = create_hypothesis(
                    store,
                    ticker=query.ticker,
                    information_cutoff=cutoff.information_cutoff,
                    provenance="historical_replay",
                    event_type=query.event_type,
                    direction=direction,
                    horizon_days=horizon_days,
                    predicted_probability=selected.forecast_probability,
                    base_rate=selected.base_rate,
                    sample_size=selected.n,
                    as_of=as_of,
                    evidence_ids=[match.event.event_id for match in study.matches],
                    forecast_algo_version="analogue-v1",
                    relaxation_level=study.relaxation_level,
                    base_rate_scope=selected.base_rate_scope,
                    analogue_count=len(study.matches),
                )
            finally:
                store.close()
        return TimeMachineForecast(
            ticker=query.ticker,
            as_of=as_of,
            information_cutoff=cutoff.information_cutoff,
            event=query,
            matches=[_match_payload(match, cutoff.information_cutoff.date()) for match in study.matches],
            distributions=statistics,
            relaxation_level=study.relaxation_level,
            insufficient_analogues=study.insufficient_analogues,
            hypothesis_id=hypothesis.id if hypothesis else None,
        )

    def reveal(self, hypothesis_id: UUID, now: date | None = None) -> TimeMachineReveal:
        store = LedgerStore(self.database)
        try:
            hypothesis = get_hypothesis(store, hypothesis_id)
            if hypothesis.provenance != "historical_replay":
                raise HTTPException(status_code=422, detail="Only historical replay hypotheses can be revealed")
            current_date = now or datetime.now(UTC).date()
            if current_date < hypothesis.resolve_after:
                return TimeMachineReveal(
                    hypothesis_id=hypothesis.id,
                    revealed=False,
                    resolve_after=hypothesis.resolve_after,
                    status=hypothesis.status,
                    status_reason="Outcome horizon has not elapsed",
                )
            resolution = resolve_hypothesis(store, hypothesis, now=current_date)
            refreshed = get_hypothesis(store, hypothesis.id)
            return TimeMachineReveal(
                hypothesis_id=hypothesis.id,
                revealed=resolution is not None,
                resolve_after=refreshed.resolve_after,
                status=refreshed.status,
                status_reason=refreshed.status_reason,
                resolution=resolution,
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        finally:
            store.close()


def _match_payload(match: AnalogueMatch, cutoff: date) -> TimeMachineMatch:
    event = match.event

    def visible(horizon: str) -> float | None:
        end_date = getattr(event, f"{horizon}_end")
        return getattr(event, horizon) if end_date is not None and end_date < cutoff else None

    return TimeMachineMatch(
        event_id=event.event_id,
        ticker=event.ticker,
        event_date=event.event_date,
        event_type=event.event_type,
        headline=event.headline,
        source_url=event.source_url,
        similarity=match.similarity,
        feature_scores=match.feature_scores,
        retrieval_source=match.retrieval_source,
        relaxation_level=match.relaxation_level,
        forward_returns=TimeMachineForwardReturns(
            fwd_1d=visible("fwd_1d"),
            fwd_5d=visible("fwd_5d"),
            fwd_20d=visible("fwd_20d"),
            fwd_60d=visible("fwd_60d"),
        ),
    )
