from datetime import UTC, date, datetime
import json
from pathlib import Path

import pytest

from quantmind.sec_events import parse_8k_pages, parse_8k_submissions
from quantmind.events import DailyMarketRow, EventRecord, classify_price_event, compute_forward_return
from quantmind.sec_events import FilingEvent
from scripts.backfill_memory import filing_reaction_date


def test_event_record_text_round_trip() -> None:
    record = EventRecord(
        ticker="CRM",
        event_date=date(2025, 1, 2),
        event_type="price_move",
        return_1d=5.0,
        volume_ratio=2.5,
        close=300.0,
    )
    assert EventRecord.from_memory_text(record.to_memory_text()) == record


def test_classifier_rules() -> None:
    row = DailyMarketRow(
        event_date=date(2025, 1, 2),
        close=100,
        return_1d=0.04,
        return_5d=0.02,
        volume_ratio=2.5,
        high=101,
        low=95,
        abnormal_sigma=0.01,
    )
    assert classify_price_event(row) == "price_only"
    assert classify_price_event(row.model_copy(update={"volume_ratio": 1.0, "return_1d": 0.06})) == "price_only"
    assert classify_price_event(row.model_copy(update={"volume_ratio": 1.0, "return_1d": -0.05})) == "price_only"


def test_forward_return_computation() -> None:
    assert compute_forward_return([100, 101, 102, 103, 104, 110], 0) == pytest.approx(10.0)
    assert compute_forward_return([100, 101], 0) is None


def test_after_close_filing_uses_next_trading_session() -> None:
    rows = [
        DailyMarketRow(
            event_date=date(2024, 1, 4),
            close=100,
            return_1d=0,
            return_5d=0,
            volume_ratio=1,
            high=100,
            low=100,
        ),
        DailyMarketRow(
            event_date=date(2024, 1, 5),
            close=101,
            return_1d=0.01,
            return_5d=0,
            volume_ratio=1,
            high=101,
            low=100,
        ),
    ]
    filing = FilingEvent(
        ticker="CRM",
        event_date=date(2024, 1, 4),
        event_type="restructuring_layoffs",
        item_code="2.05",
        headline="After-close filing",
        filing_url="https://www.sec.gov/example",
        available_at=datetime(2024, 1, 4, 21, 30, tzinfo=UTC),
    )
    assert filing_reaction_date(filing, rows) == date(2024, 1, 5)


def test_filing_before_stored_window_is_not_shifted_to_latest_session() -> None:
    rows = [
        DailyMarketRow(
            event_date=date(2024, 1, 4),
            close=100,
            return_1d=0,
            return_5d=0,
            volume_ratio=1,
            high=100,
            low=100,
        ),
    ]
    filing = FilingEvent(
        ticker="CRM",
        event_date=date(2023, 12, 1),
        event_type="earnings_release",
        item_code="2.02",
        headline="Older filing",
        filing_url="https://www.sec.gov/example",
        available_at=datetime(2023, 12, 1, 15, 0, tzinfo=UTC),
    )
    assert filing_reaction_date(filing, rows) is None


def test_real_8k_item_fixture_classifies_and_builds_source_url() -> None:
    fixture = json.loads((Path(__file__).parent / "fixtures" / "sec_8k_recent.json").read_text())
    payload = {"filings": {"recent": fixture["filings"]["recent"]}}
    older = fixture["older"]
    events = parse_8k_pages("CRM", "0001234567", [payload, older])
    assert [(event.item_code, event.event_type) for event in events] == [
        ("1.01", "material_agreement"),
        ("5.02", "leadership_change"),
        ("2.05", "restructuring_layoffs"),
    ]
    assert events[0].filing_url.endswith("/000123456725000001/contract.htm")
    assert any(event.event_date.isoformat() == "2024-01-04" for event in events)
