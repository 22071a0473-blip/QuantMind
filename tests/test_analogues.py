from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from quantmind.analogue_stats import compute_statistics, stable_seed
from quantmind.analogues import AnalogueMatch, EventQuery, feature_scores, retrieve_analogues, similarity
from quantmind.event_store import EventStore, MarketEvent, deterministic_event_id


def event(index: int, event_type: str = "contract_win", sector: str = "Technology") -> MarketEvent:
    event_date = date(2020, 1, 1) + timedelta(days=index)
    source_url = f"https://example.test/{index}"
    return MarketEvent(
        event_id=deterministic_event_id("CRM", event_date, event_type, source_url),
        ticker="CRM",
        sector=sector,
        event_date=event_date,
        available_at=datetime.combine(event_date, datetime.min.time(), tzinfo=UTC),
        event_type=event_type,
        headline=f"Event {index}",
        source_url=source_url,
        source_kind="fixture",
        day0_abnormal_return=0.03 if index % 2 else 0.02,
        volume_ratio=2.0,
        pre_drift_20d=0.01,
        regime_spy_ret_60d=0.04,
        regime_spy_vol_60d=0.02,
        fwd_20d=0.05 if index % 2 else -0.02,
        fwd_1d_end=event_date + timedelta(days=1),
        fwd_5d_end=event_date + timedelta(days=5),
        fwd_20d_end=event_date + timedelta(days=20),
        fwd_60d_end=event_date + timedelta(days=60),
    )


def test_event_id_is_stable() -> None:
    assert deterministic_event_id("crm", date(2024, 1, 2), "earnings", "https://x") == deterministic_event_id(
        "CRM", date(2024, 1, 2), "earnings", "https://x"
    )


def test_event_store_upsert_is_idempotent(tmp_path: Path) -> None:
    store = EventStore(tmp_path / "events.db")
    try:
        record = event(1)
        store.upsert(record)
        store.upsert(record.model_copy(update={"headline": "Updated"}))
        rows = store.list_events(ticker="CRM")
        assert len(rows) == 1
        assert rows[0].headline == "Updated"
    finally:
        store.close()


def test_retrieval_excludes_future_and_self() -> None:
    corpus = [event(index) for index in range(12)]
    query = EventQuery(
        event_id=corpus[-1].event_id,
        ticker="CRM",
        event_date=date(2020, 1, 20),
        available_at=datetime(2020, 1, 20, tzinfo=UTC),
        event_type="contract_win",
        sector="Technology",
        day0_abnormal_return=0.03,
        volume_ratio=2.0,
        pre_drift_20d=0.01,
        regime_spy_ret_60d=0.04,
        regime_spy_vol_60d=0.02,
    )
    result = retrieve_analogues(query, corpus, query.available_at)
    assert all(match.event.event_id != query.event_id for match in result.matches)
    assert all(match.event.available_at < query.available_at for match in result.matches)


def test_statistics_are_deterministic_and_shrunk() -> None:
    matches = [
        AnalogueMatch(
            event=event(index).model_copy(update={"fwd_20d": 0.1 if index < 4 else -0.1}),
            similarity=0.8,
            feature_scores={},
        )
        for index in range(6)
    ]
    result = compute_statistics(matches, all_event_returns=[-0.1] * 20)
    assert result.n == 6
    assert result.hit_rate == 4 / 6
    assert result.forecast_probability is not None
    assert result.forecast_probability < result.hit_rate


def test_forward_statistics_censor_each_horizon_by_end_date() -> None:
    matches = [
        AnalogueMatch(
            event=event(index).model_copy(
                update={
                    "fwd_5d": 0.1,
                    "fwd_20d": 0.1,
                    "fwd_60d": 0.1,
                    "fwd_5d_end": date(2024, 1, 10),
                    "fwd_20d_end": date(2024, 1, 20),
                    "fwd_60d_end": date(2024, 3, 10),
                }
            ),
            similarity=0.8,
            feature_scores={},
        )
        for index in range(6)
    ]
    cutoff = date(2024, 2, 1)
    assert compute_statistics(matches, "fwd_5d", cutoff=cutoff).n == 6
    assert compute_statistics(matches, "fwd_20d", cutoff=cutoff).n == 6
    assert compute_statistics(matches, "fwd_60d", cutoff=cutoff).n == 0


def test_null_features_are_excluded_and_weights_renormalize() -> None:
    query = EventQuery(
        ticker="CRM",
        event_date=date(2025, 1, 1),
        available_at=datetime(2025, 1, 2, tzinfo=UTC),
        event_type="contract_win",
        sector="Technology",
        day0_abnormal_return=0.02,
        volume_ratio=2.0,
    )
    candidate = event(1).model_copy(
        update={
            "market_cap_bucket": None,
            "pre_drift_20d": None,
            "regime_spy_ret_60d": None,
            "regime_spy_vol_60d": None,
        }
    )
    scores = feature_scores(query, candidate, [candidate])
    assert scores.market_cap_bucket is None
    assert similarity(query, candidate, [candidate]) == 1.0


def test_bootstrap_seed_is_stable_and_cutoff_sensitive() -> None:
    first = stable_seed("event-1", "fwd_20d", date(2025, 1, 1))
    second = stable_seed("event-1", "fwd_20d", date(2025, 1, 1))
    changed = stable_seed("event-1", "fwd_20d", date(2025, 1, 2))
    assert first == second
    assert first != changed


def test_underperform_probability_is_complementary() -> None:
    matches = [
        AnalogueMatch(
            event=event(index).model_copy(update={"fwd_20d": 0.1 if index < 4 else -0.1}),
            similarity=0.8,
            feature_scores={},
        )
        for index in range(6)
    ]
    outperform = compute_statistics(matches, all_event_returns=[0.1] * 20)
    underperform = compute_statistics(matches, all_event_returns=[0.1] * 20, direction="underperform")
    assert underperform.forecast_probability == 1 - outperform.forecast_probability


def test_precedent_rejects_future_cutoff_and_is_empty_without_events(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("QUANTMIND_DATABASE", str(tmp_path / "empty.db"))
    from quantmind.app import app

    client = TestClient(app)
    response = client.get("/api/precedent/CRM?cutoff=2999-01-01T00:00:00Z")
    assert response.status_code == 422
    response = client.get("/api/precedent/CRM")
    assert response.status_code == 200
    assert response.json()["status"] == "no_event"
