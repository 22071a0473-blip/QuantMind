import asyncio
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from quantmind.app import app
from quantmind.current_event import detect_current_event
from quantmind.event_store import EventStore, MarketEvent
from quantmind.ledger_store import LedgerStore
from quantmind.storage import CompanyRecord, MarketBarRecord, SecurityRecord, SQLiteStore
from quantmind.timemachine import TimeMachineService


def _seed_time_machine_database(path: Path) -> date:
    structured = SQLiteStore(path)
    company_id = uuid4()
    target_id = uuid4()
    benchmark_company_id = uuid4()
    benchmark_id = uuid4()
    structured.upsert_company(CompanyRecord(company_id=company_id, legal_name="Replay Target", is_public=True))
    structured.upsert_company(CompanyRecord(company_id=benchmark_company_id, legal_name="Replay Benchmark", is_public=True))
    structured.upsert_security(SecurityRecord(security_id=target_id, company_id=company_id, ticker="TEST"))
    structured.upsert_security(SecurityRecord(security_id=benchmark_id, company_id=benchmark_company_id, ticker="SPY"))
    start = datetime(2024, 1, 2, 21, tzinfo=UTC)
    dates: list[date] = []
    target_bars: list[MarketBarRecord] = []
    benchmark_bars: list[MarketBarRecord] = []
    for index in range(160):
        observed = start + timedelta(days=index)
        dates.append(observed.date())
        target_price = 100 + index
        benchmark_price = 100 + index / 2
        target_bars.append(_bar(target_id, observed, target_price))
        benchmark_bars.append(_bar(benchmark_id, observed, benchmark_price))
    structured.upsert_market_bars(target_bars + benchmark_bars)
    structured.close()

    query_date = dates[130]
    events = EventStore(path)
    try:
        for index in range(20, 100, 8):
            events.upsert(_event(dates[index], index, query_date))
        events.upsert(_event(dates[125], 125, query_date))
        events.upsert(_event(query_date, 130, query_date))
    finally:
        events.close()
    return query_date


def _bar(security_id, observed: datetime, price: float) -> MarketBarRecord:
    return MarketBarRecord(
        security_id=security_id,
        observed_at=observed,
        open=price,
        high=price,
        low=price,
        close=price,
        adjusted_close=price,
        volume=100,
        provider="fixture",
        available_at=observed + timedelta(hours=1),
    )


def _event(event_date: date, index: int, query_date: date) -> MarketEvent:
    return MarketEvent(
        event_id=f"event-{index}",
        ticker="TEST",
        sector="Technology",
        event_date=event_date,
        available_at=datetime.combine(event_date, datetime.min.time(), tzinfo=UTC) + timedelta(hours=12),
        event_type="price_only",
        headline=f"TEST event {index}",
        source_url=f"https://example.test/events/{index}",
        source_kind="fixture",
        day0_abnormal_return=0.01,
        volume_ratio=2.0,
        pre_drift_20d=0.01,
        regime_spy_ret_60d=0.02,
        regime_spy_vol_60d=0.01,
        fwd_1d=1.0,
        fwd_5d=2.0,
        fwd_20d=3.0,
        fwd_60d=4.0,
        fwd_1d_end=event_date + timedelta(days=1),
        fwd_5d_end=event_date + timedelta(days=5),
        fwd_20d_end=event_date + timedelta(days=20),
        fwd_60d_end=query_date + timedelta(days=1),
    )


def test_time_machine_forecast_redacts_post_cutoff_outcomes(tmp_path: Path) -> None:
    database = tmp_path / "quantmind.db"
    query_date = _seed_time_machine_database(database)
    service = TimeMachineService(database)
    forecast = asyncio.run(service.forecast("TEST", query_date, 5))
    assert forecast.provenance == "historical_replay"
    assert forecast.information_cutoff == datetime.combine(query_date + timedelta(days=1), datetime.min.time(), tzinfo=UTC)
    assert forecast.matches
    assert any(match.forward_returns.fwd_5d is not None for match in forecast.matches)
    assert all(match.forward_returns.fwd_60d is None for match in forecast.matches)
    assert forecast.hypothesis_id is not None
    assert "realized_abnormal_return" not in forecast.model_dump()


def test_time_machine_forecast_is_unchanged_by_future_event_injection(tmp_path: Path) -> None:
    database = tmp_path / "quantmind.db"
    query_date = _seed_time_machine_database(database)
    service = TimeMachineService(database)
    before = asyncio.run(service.forecast("TEST", query_date, 5))
    events = EventStore(database)
    try:
        events.upsert(_event(query_date + timedelta(days=10), 999, query_date))
    finally:
        events.close()
    after = asyncio.run(service.forecast("TEST", query_date, 5))
    assert [match.event_id for match in before.matches] == [match.event_id for match in after.matches]
    assert before.distributions == after.distributions


def test_time_machine_dry_run_does_not_persist_hypothesis(tmp_path: Path) -> None:
    database = tmp_path / "quantmind.db"
    query_date = _seed_time_machine_database(database)
    forecast = asyncio.run(TimeMachineService(database).forecast("TEST", query_date, 5, persist_hypothesis=False))
    assert forecast.hypothesis_id is None
    store = LedgerStore(database)
    try:
        assert store.count_hypotheses(provenance="historical_replay") == 0
    finally:
        store.close()


def test_time_machine_candidates_are_paginated_and_cutoff_safe(tmp_path: Path) -> None:
    database = tmp_path / "quantmind.db"
    query_date = _seed_time_machine_database(database)
    page = TimeMachineService(database).candidates("TEST", limit=1, offset=0)
    assert page.total >= 1
    assert len(page.items) == 1
    assert page.items[0].as_of == query_date
    assert page.items[0].history_days >= 120


def test_time_machine_forecast_route_rejects_future_dates(tmp_path: Path, monkeypatch) -> None:
    database = tmp_path / "quantmind.db"
    monkeypatch.setenv("QUANTMIND_DATABASE", str(database))
    client = TestClient(app)
    response = client.post(
        "/api/timemachine/forecast",
        json={"ticker": "TEST", "as_of": "2999-01-01", "horizon_days": 5},
    )
    assert response.status_code == 422


def test_current_event_excludes_bars_available_after_cutoff(tmp_path: Path, monkeypatch) -> None:
    database = tmp_path / "quantmind.db"
    query_date = _seed_time_machine_database(database)
    monkeypatch.setenv("QUANTMIND_DATABASE", str(database))
    cutoff = datetime.combine(query_date + timedelta(days=1), datetime.min.time(), tzinfo=UTC)
    event = detect_current_event("TEST", cutoff)
    assert event is not None
    assert event.event_date == query_date
