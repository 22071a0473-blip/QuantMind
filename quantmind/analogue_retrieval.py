"""Service boundary for structured analogue retrieval and event-study statistics."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from .analogue_stats import AnalogueStatistics, compute_statistics, stable_seed
from .analogues import AnalogueMatch, EventQuery, retrieve_analogues
from .event_memory import QuantMindEventMemory
from .event_store import EventStore, MarketEvent


class AnalogueStudy(BaseModel):
    query: EventQuery
    matches: list[AnalogueMatch] = Field(default_factory=list)
    statistics: dict[str, AnalogueStatistics] = Field(default_factory=dict)
    relaxation_level: str
    semantic_status: str = "not_requested"
    semantic_reason: str | None = None
    insufficient_analogues: bool = False


class AnalogueService:
    def __init__(self, database: Path = Path("data/quantmind.db")) -> None:
        self._database = database

    def study(
        self,
        query: EventQuery,
        *,
        cutoff: datetime | None = None,
        horizons: tuple[str, ...] = ("fwd_1d", "fwd_5d", "fwd_20d", "fwd_60d"),
    ) -> AnalogueStudy:
        effective_cutoff = cutoff or query.available_at
        store = EventStore(self._database)
        try:
            corpus = store.list_events(limit=10_000)
        finally:
            store.close()
        retrieval = retrieve_analogues(query, corpus, effective_cutoff)
        statistics = {
            horizon: compute_statistics(
                retrieval.matches,
                horizon,
                all_event_returns=[
                    value
                    for event in corpus
                    if event.available_at < effective_cutoff
                    and getattr(event, f"{horizon}_end", None) is not None
                    and getattr(event, f"{horizon}_end") < effective_cutoff.date()
                    and (value := getattr(event, horizon, None)) is not None
                ],
                cutoff=effective_cutoff.date(),
                seed=stable_seed(query.event_id or "", horizon, effective_cutoff.date()),
            )
            for horizon in horizons
        }
        return AnalogueStudy(
            query=query,
            matches=retrieval.matches,
            statistics=statistics,
            relaxation_level=retrieval.relaxation_level,
            insufficient_analogues=retrieval.insufficient_analogues,
            semantic_status="not_requested",
        )

    async def astudy(
        self,
        query: EventQuery,
        *,
        cutoff: datetime | None = None,
        horizons: tuple[str, ...] = ("fwd_1d", "fwd_5d", "fwd_20d", "fwd_60d"),
    ) -> AnalogueStudy:
        effective_cutoff = cutoff or query.available_at
        store = EventStore(self._database)
        try:
            corpus = store.list_events(limit=10_000)
        finally:
            store.close()
        semantic_events: list[MarketEvent] = []
        semantic_status = "unavailable"
        semantic_reason: str | None = None
        try:
            hits = await QuantMindEventMemory().search(
                f"{query.ticker} {query.event_type} {query.sector or ''}",
                limit=20,
            )
            semantic_status = "available"
            for hit in hits:
                event = next(
                    (candidate for candidate in corpus if candidate.hindsight_document_id == hit.result_id),
                    None,
                )
                if event is not None:
                    semantic_events.append(event)
        except KeyError:
            semantic_reason = "Hindsight credentials are not configured."
        except Exception as exc:
            status_code = getattr(exc, "status_code", None) or getattr(exc, "status", None)
            if status_code in (401, 403):
                semantic_status = "unauthorized"
                semantic_reason = "Hindsight rejected the configured credentials."
            else:
                semantic_reason = "Hindsight semantic retrieval is unavailable."
        retrieval = retrieve_analogues(query, corpus, effective_cutoff, semantic_events=semantic_events)
        statistics = {
            horizon: compute_statistics(
                retrieval.matches,
                horizon,
                all_event_returns=[
                    value
                    for event in corpus
                    if event.available_at < effective_cutoff
                    and getattr(event, f"{horizon}_end", None) is not None
                    and getattr(event, f"{horizon}_end") < effective_cutoff.date()
                    and (value := getattr(event, horizon, None)) is not None
                ],
                cutoff=effective_cutoff.date(),
                seed=stable_seed(query.event_id or "", horizon, effective_cutoff.date()),
            )
            for horizon in horizons
        }
        return AnalogueStudy(
            query=query,
            matches=retrieval.matches,
            statistics=statistics,
            relaxation_level=retrieval.relaxation_level,
            semantic_status=semantic_status,
            semantic_reason=semantic_reason,
            insufficient_analogues=retrieval.insufficient_analogues,
        )

    def latest_event(self, ticker: str, now: datetime | None = None) -> MarketEvent | None:
        effective_now = now or datetime.now(UTC)
        store = EventStore(self._database)
        try:
            events = store.list_events(ticker=ticker, cutoff=effective_now, limit=1)
            return events[0] if events else None
        finally:
            store.close()
