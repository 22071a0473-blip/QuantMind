from datetime import UTC, date, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from quantmind.cutoff import Cutoff, cutoff_for_as_of
from quantmind.returns import forward_abnormal_return
from quantmind.storage import CompanyRecord, MarketBarRecord, SecurityRecord, SQLiteStore


def _seed_bars(path: Path, *, include_benchmark: bool = True) -> None:
    store = SQLiteStore(path)
    company_id = uuid4()
    target_id = uuid4()
    store.upsert_company(CompanyRecord(company_id=company_id, legal_name="Target", is_public=True))
    store.upsert_security(SecurityRecord(security_id=target_id, company_id=company_id, ticker="TEST"))
    benchmark_id = uuid4()
    if include_benchmark:
        benchmark_company_id = uuid4()
        store.upsert_company(CompanyRecord(company_id=benchmark_company_id, legal_name="Benchmark", is_public=True))
        store.upsert_security(SecurityRecord(security_id=benchmark_id, company_id=benchmark_company_id, ticker="SPY"))
    for index in range(5):
        observed = datetime(2024, 1, 2 + index, 21, tzinfo=UTC)
        store.upsert_market_bars(
            [
                _bar(target_id, observed, 100 + index * 10),
                *(
                    [_bar(benchmark_id, observed, 100 + index * 5)]
                    if include_benchmark
                    else []
                ),
            ]
        )
    store.close()


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
        available_at=observed + datetime.resolution,
    )


def test_cutoff_is_exclusive_start_of_next_utc_day() -> None:
    cutoff = cutoff_for_as_of(date(2024, 1, 5))
    assert cutoff == Cutoff(
        as_of=date(2024, 1, 5),
        information_cutoff=datetime(2024, 1, 6, tzinfo=UTC),
    )


def test_cutoff_rejects_naive_or_inconsistent_timestamps() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        Cutoff(date(2024, 1, 5), datetime(2024, 1, 6))
    with pytest.raises(ValueError, match="exclusive day"):
        Cutoff(date(2024, 1, 5), datetime(2024, 1, 5, tzinfo=UTC))


def test_forward_return_uses_close_entry_and_benchmark_relative_path(tmp_path: Path) -> None:
    database = tmp_path / "quantmind.db"
    _seed_bars(database)
    result = forward_abnormal_return("TEST", date(2024, 1, 2), 2, database=database)
    assert result is not None
    assert result.start_date == date(2024, 1, 2)
    assert result.end_date == date(2024, 1, 4)
    assert result.raw_return == pytest.approx(20.0)
    assert result.benchmark_return == pytest.approx(10.0)
    assert result.abnormal_return == pytest.approx(10.0)
    assert result.path == pytest.approx((0.0, 5.0, 10.0))


def test_forward_return_requires_benchmark_and_complete_horizon(tmp_path: Path) -> None:
    database = tmp_path / "quantmind.db"
    _seed_bars(database, include_benchmark=False)
    assert forward_abnormal_return("TEST", date(2024, 1, 2), 1, database=database) is None
    with pytest.raises(ValueError, match="positive"):
        forward_abnormal_return("TEST", date(2024, 1, 2), 0, database=database)


def test_forward_return_rejects_as_of_bars_not_available_at_cutoff(tmp_path: Path) -> None:
    database = tmp_path / "quantmind.db"
    _seed_bars(database)
    cutoff = datetime(2024, 1, 2, 20, tzinfo=UTC)
    assert (
        forward_abnormal_return(
            "TEST",
            date(2024, 1, 2),
            1,
            database=database,
            information_cutoff=cutoff,
        )
        is None
    )
