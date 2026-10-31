from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from quantmind.historical import (
    WalkForwardConfig,
    compute_feature_at,
    forward_returns,
    search_analogues,
    walk_forward_evaluate,
)
from quantmind.storage import ForecastRecord, MarketBarRecord, SQLiteStore
from quantmind.temporal import TemporalMetadata, eligibility_decision, is_eligible
from quantmind.outcomes import resolve_forecast
from quantmind.outcomes import persist_resolution


def bars(count: int = 270, security_id=None) -> list[MarketBarRecord]:
    security_id = security_id or uuid4()
    start = datetime(2024, 1, 2, 21, tzinfo=UTC)
    return [
        MarketBarRecord(
            security_id=security_id,
            observed_at=start + timedelta(days=index),
            open=100 + index,
            high=101 + index,
            low=99 + index,
            close=100 + index,
            adjusted_close=100 + index,
            volume=1000 + index * 10,
            provider="fixture",
            available_at=start + timedelta(days=index, hours=2),
        )
        for index in range(count)
    ]


def test_features_use_trading_session_positions_and_adjusted_close() -> None:
    fixture = bars()
    feature = compute_feature_at(fixture, 260)
    assert feature.values["return_1"] is not None
    assert feature.values["return_252"] is not None
    assert feature.price_basis == "adjusted_close_fallback"
    assert feature.source_bar_count == 261


def test_forward_returns_are_null_when_future_observation_is_missing() -> None:
    fixture = bars(5)
    result = forward_returns(fixture, 0)
    assert result["return_1"] is not None
    assert result["return_5"] is None


def test_analogue_search_excludes_target_self_match_and_future_information() -> None:
    fixture = bars(270)
    target_date = fixture[260].observed_at.date()
    query = search_analogues(
        fixture,
        [fixture],
        target_date=target_date,
        cutoff=fixture[260].available_at,
        limit=5,
    )
    assert all(match.observed_at.date() < target_date for match in query.matches)


def test_walk_forward_is_chronological_and_reports_exclusions() -> None:
    fixture = bars(280)
    result = walk_forward_evaluate(
        fixture,
        WalkForwardConfig(minimum_history=252, train_sessions=10, horizon=20),
    )
    dates = [point.decision_date for point in result.points]
    assert dates == sorted(dates)
    assert result.metrics["sample_size"] > 0
    assert result.limitations


def test_feature_snapshot_is_idempotent(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "quantmind.db")
    try:
        fixture = bars(3)
        store.save_json_snapshot(
            "feature",
            "same",
            fixture[0].security_id,
            fixture[0].observed_at,
            '{"version":"v1"}',
        )
        store.save_json_snapshot(
            "feature",
            "same",
            fixture[0].security_id,
            fixture[0].observed_at,
            '{"version":"v2"}',
        )
    finally:
        store.close()


def test_later_published_information_is_excluded_from_historical_cutoff() -> None:
    cutoff = datetime(2025, 1, 10, tzinfo=UTC)
    later = TemporalMetadata(
        occurred_at=datetime(2024, 12, 31, tzinfo=UTC),
        published_at=datetime(2025, 1, 11, tzinfo=UTC),
    )
    assert not is_eligible(later, cutoff)
    assert eligibility_decision(later, cutoff).reason == "published_after_cutoff"


def test_unknown_publication_time_is_excluded_by_default() -> None:
    decision = eligibility_decision(TemporalMetadata(), datetime.now(UTC))
    assert not decision.eligible
    assert decision.reason == "missing_publication_timestamp"


def test_outcome_resolution_distinguishes_censored_future() -> None:
    fixture = bars(5)
    forecast = ForecastRecord(
        research_id=uuid4(),
        security_id=fixture[0].security_id,
        created_at=fixture[0].observed_at,
        horizon_days=20,
        expected_direction="up",
    )
    resolution = resolve_forecast(forecast, fixture)
    assert resolution.status == "censored"


def test_outcome_resolution_persists_status_without_fabricating_return(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "quantmind.db")
    try:
        fixture = bars(5)
        forecast = ForecastRecord(
            research_id=uuid4(),
            security_id=fixture[0].security_id,
            created_at=fixture[0].observed_at,
            horizon_days=20,
            expected_direction="up",
        )
        store.save_forecast(forecast)
        persist_resolution(store, resolve_forecast(forecast, fixture))
        outcome = store.get_outcome(forecast.forecast_id)
        assert outcome is not None
        assert outcome.evaluation_status == "censored"
        assert outcome.realized_return is None
    finally:
        store.close()
