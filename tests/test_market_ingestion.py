from datetime import UTC, date, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from quantmind.market_ingestion import (
    ProviderMarketRow,
    MarketIngestionResult,
    checkpoint_for,
    ingest_market_history,
    to_market_bars,
    validate_market_rows,
)
from quantmind.storage import CompanyRecord, IngestionJobRecord, SecurityRecord, SQLiteStore


def row(day: int, close: float = 10.0) -> ProviderMarketRow:
    return ProviderMarketRow(
        observed_at=datetime(2025, 1, day, 21, tzinfo=UTC),
        open=close - 1,
        high=close + 1,
        low=close - 1,
        close=close,
        volume=100,
    )


def test_normalization_sorts_and_deduplicates_for_validation() -> None:
    security_id = uuid4()
    result = validate_market_rows(security_id, [row(3), row(2), row(2)])
    assert [item.observed_at.day for item in result.accepted] == [2, 3]
    assert result.duplicate_count == 1


def test_validation_rejects_bad_ohlc_and_flags_long_gaps() -> None:
    security_id = uuid4()
    invalid = ProviderMarketRow(
        observed_at=datetime(2025, 1, 2, tzinfo=UTC),
        open=10,
        high=8,
        low=9,
        close=10,
    )
    result = validate_market_rows(security_id, [row(1), invalid, row(15)])
    assert any(issue.issue_code == "invalid_ohlc" for issue in result.issues)
    assert any(issue.issue_code == "missing_interval" for issue in result.issues)


def test_normalization_preserves_adjusted_close_and_availability() -> None:
    security_id = uuid4()
    source_row = row(2)
    source_row = source_row.model_copy(
        update={
            "adjusted_close": 9.5,
            "available_at": datetime(2025, 1, 3, 2, tzinfo=UTC),
        }
    )
    bar = to_market_bars(security_id, [source_row], "fixture")[0]
    assert bar.adjusted_close == 9.5
    assert bar.available_at.date().isoformat() == "2025-01-03"


def test_checkpoint_uses_last_accepted_observation() -> None:
    security_id = uuid4()
    quality = validate_market_rows(security_id, [row(2), row(3)])
    result = MarketIngestionResult(job=IngestionJobRecord(job_type="test"), quality=quality, stored_bars=2)
    checkpoint = checkpoint_for(result, "EXM", security_id, "fixture")
    assert checkpoint is not None
    assert checkpoint.last_completed == date(2025, 1, 3)


class FakeProvider:
    name = "fixture"

    def __init__(self) -> None:
        self.calls = 0

    async def daily_history(self, ticker: str, start: date, end: date) -> list[ProviderMarketRow]:
        self.calls += 1
        return [row(2), row(3)]


class FlakyProvider(FakeProvider):
    async def daily_history(self, ticker: str, start: date, end: date) -> list[ProviderMarketRow]:
        self.calls += 1
        if self.calls < 3:
            raise RuntimeError("temporary provider failure")
        return [row(2)]


@pytest.mark.asyncio
async def test_ingestion_is_idempotent_and_records_job(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "quantmind.db")
    try:
        company = CompanyRecord(legal_name="Example", is_public=True)
        security = SecurityRecord(company_id=company.company_id, ticker="EXM")
        store.upsert_company(company)
        store.upsert_security(security)
        provider = FakeProvider()
        first = await ingest_market_history(
            store, provider, security.security_id, "EXM", date(2025, 1, 1), date(2025, 1, 5)
        )
        second = await ingest_market_history(
            store, provider, security.security_id, "EXM", date(2025, 1, 1), date(2025, 1, 5)
        )
        assert first.stored_bars == 2
        assert second.stored_bars == 2
        assert store.coverage().market_bars == 2
        assert store.coverage().ingestion_jobs == 2
    finally:
        store.close()


@pytest.mark.asyncio
async def test_ingestion_retries_bounded_provider_failures(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "quantmind.db")
    try:
        company = CompanyRecord(legal_name="Retry Example", is_public=True)
        security = SecurityRecord(company_id=company.company_id, ticker="TRY")
        store.upsert_company(company)
        store.upsert_security(security)
        provider = FlakyProvider()
        result = await ingest_market_history(
            store, provider, security.security_id, "TRY", date(2025, 1, 1), date(2025, 1, 5), retries=2
        )
        assert result.job.retry_count == 2
        assert provider.calls == 3
    finally:
        store.close()
