from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from quantmind.forecast import baseline_forecast
from quantmind.ledger import HypothesisOverrides, create_hypothesis, supersede, verify_record, view
from quantmind.ledger_store import LedgerStore
from quantmind.resolver import resolve_hypothesis
from quantmind.storage import CompanyRecord, MarketBarRecord, SecurityRecord, SQLiteStore


def seed_market(path: Path, *, days: int = 80) -> None:
    structured = SQLiteStore(path)
    target_id = uuid4()
    benchmark_id = uuid4()
    company_id = uuid4()
    benchmark_company_id = uuid4()
    start = datetime(2024, 1, 2, 21, tzinfo=UTC)
    structured.upsert_company(CompanyRecord(company_id=company_id, legal_name="Example Corp", is_public=True))
    structured.upsert_company(CompanyRecord(company_id=benchmark_company_id, legal_name="Benchmark ETF", is_public=True))
    structured.upsert_security(SecurityRecord(security_id=target_id, company_id=company_id, ticker="TEST"))
    structured.upsert_security(SecurityRecord(security_id=benchmark_id, company_id=benchmark_company_id, ticker="SPY"))
    target = []
    benchmark = []
    for index in range(days):
        observed = start + timedelta(days=index)
        target_price = 100 + index * 0.6
        benchmark_price = 100 + index * 0.2
        target.append(_bar(target_id, observed, target_price))
        benchmark.append(_bar(benchmark_id, observed, benchmark_price))
    structured.upsert_market_bars(target + benchmark)
    structured.close()


def _bar(security_id, observed: datetime, price: float) -> MarketBarRecord:
    return MarketBarRecord(
        security_id=security_id,
        observed_at=observed,
        open=price,
        high=price + 1,
        low=price - 1,
        close=price,
        adjusted_close=price,
        volume=1000,
        provider="fixture",
        available_at=observed + timedelta(hours=2),
    )


def _hypothesis(store: LedgerStore):
    return create_hypothesis(
        store,
        ticker="TEST",
        information_cutoff=datetime(2024, 1, 2, 20, tzinfo=UTC),
        provenance="live_forward",
        event_type="price_only",
        direction="outperform",
        horizon_days=5,
        predicted_probability=0.65,
        base_rate=0.65,
        sample_size=40,
    )


def test_ledger_creation_is_deduplicated_and_hash_verifies(tmp_path: Path) -> None:
    database = tmp_path / "quantmind.db"
    seed_market(database)
    store = LedgerStore(database)
    try:
        first = _hypothesis(store)
        second = _hypothesis(store)
        assert first.id == second.id
        assert verify_record(store, first.id)
        assert view(store, first.id).verified
    finally:
        store.close()


def test_hypothesis_is_immutable_except_status(tmp_path: Path) -> None:
    database = tmp_path / "quantmind.db"
    seed_market(database)
    store = LedgerStore(database)
    try:
        hypothesis = _hypothesis(store)
        with pytest.raises(Exception, match="append-only"):
            store.connection.execute(
                "UPDATE hypotheses SET claim_text = ? WHERE id = ?",
                ("tampered", str(hypothesis.id)),
            )
        store.update_status(hypothesis.id, "invalidated", "fixture")
        assert store.get_hypothesis(hypothesis.id)["status"] == "invalidated"
    finally:
        store.close()


def test_supersede_creates_a_new_linked_record(tmp_path: Path) -> None:
    database = tmp_path / "quantmind.db"
    seed_market(database)
    store = LedgerStore(database)
    try:
        original = _hypothesis(store)
        replacement = supersede(store, original.id, HypothesisOverrides(predicted_probability=0.8))
        assert replacement.id != original.id
        assert replacement.supersedes_id == original.id
        assert replacement.predicted_probability == 0.8
    finally:
        store.close()


def test_baseline_requires_thirty_complete_observations(tmp_path: Path) -> None:
    database = tmp_path / "quantmind.db"
    seed_market(database, days=25)
    store = LedgerStore(database)
    try:
        draft = baseline_forecast("TEST", store=store, horizon_days=20)
        assert not draft.available
        assert draft.sample_size < 30
    finally:
        store.close()


def test_resolver_uses_adjusted_close_and_abnormal_return(tmp_path: Path) -> None:
    database = tmp_path / "quantmind.db"
    seed_market(database)
    store = LedgerStore(database)
    try:
        hypothesis = _hypothesis(store)
        resolution = resolve_hypothesis(store, hypothesis, now=datetime(2025, 1, 1, tzinfo=UTC).date())
        assert resolution is not None
        assert resolution.realized_abnormal_return > 0
        assert resolution.start_price_date < resolution.end_price_date
        assert store.get_hypothesis(hypothesis.id)["status"] == "resolved"
    finally:
        store.close()


def test_ledger_api_commit_list_detail_and_stats(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    database = tmp_path / "quantmind.db"
    seed_market(database)
    monkeypatch.setenv("QUANTMIND_DATABASE", str(database))
    from quantmind.app import app

    client = TestClient(app)
    committed = client.post("/api/ledger/commit", json={"ticker": "TEST", "horizon_days": 20})
    assert committed.status_code == 200
    hypothesis_id = committed.json()["id"]

    listing = client.get("/api/ledger?ticker=TEST&limit=10")
    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    assert listing.json()["items"][0]["id"] == hypothesis_id

    detail = client.get(f"/api/ledger/{hypothesis_id}")
    assert detail.status_code == 200
    assert detail.json()["verified"] is True

    stats = client.get("/api/ledger/stats")
    assert stats.status_code == 200
    assert stats.json()["insufficient_data"] is True
