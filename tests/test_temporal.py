from datetime import UTC, datetime, timedelta

from quantmind.temporal import TemporalMetadata, ensure_utc, is_eligible


def test_naive_timestamp_is_normalized_to_utc() -> None:
    value = ensure_utc(datetime(2026, 1, 1, 12))
    assert value.tzinfo == UTC


def test_evidence_is_eligible_only_when_available_before_cutoff() -> None:
    cutoff = datetime(2026, 1, 10, tzinfo=UTC)
    metadata = TemporalMetadata(available_at=cutoff - timedelta(seconds=1))
    assert is_eligible(metadata, cutoff)
    assert not is_eligible(TemporalMetadata(available_at=cutoff + timedelta(seconds=1)), cutoff)


def test_unknown_timing_is_not_eligible_for_strict_history() -> None:
    cutoff = datetime(2026, 1, 10, tzinfo=UTC)
    assert not is_eligible(TemporalMetadata(), cutoff)
    assert not is_eligible(
        TemporalMetadata(available_at=cutoff - timedelta(days=1), temporal_uncertainty=True),
        cutoff,
    )
