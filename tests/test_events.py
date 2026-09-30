from datetime import date
import json
from pathlib import Path

import pytest

from quantmind.sec_events import parse_8k_pages, parse_8k_submissions
from quantmind.events import DailyMarketRow, EventRecord, classify_price_event, compute_forward_return


def test_event_record_text_round_trip() -> None:
    record = EventRecord(
        ticker="CRM", event_date=date(2025, 1, 2), event_type="price_move",
        return_1d=5.0, volume_ratio=2.5, close=300.0,
    )
    assert EventRecord.from_memory_text(record.to_memory_text()) == record


def test_classifier_rules() -> None:
    row = DailyMarketRow(
        event_date=date(2025, 1, 2), close=100, return_1d=0.04,
        return_5d=0.02, volume_ratio=2.5, high=101, low=95,
        abnormal_sigma=0.01,
    )
    assert classify_price_event(row) == "price_move"
    assert classify_price_event(row.model_copy(update={"volume_ratio": 1.0, "return_1d": 0.06})) == "price_move"
    assert classify_price_event(row.model_copy(update={"volume_ratio": 1.0, "return_1d": -0.05})) == "price_move"


def test_forward_return_computation() -> None:
    assert compute_forward_return([100, 101, 102, 103, 104, 110], 0) == pytest.approx(10.0)
    assert compute_forward_return([100, 101], 0) is None


def test_real_8k_item_fixture_classifies_and_builds_source_url() -> None:
    fixture = json.loads((Path(__file__).parent / "fixtures" / "sec_8k_recent.json").read_text())
    payload = {"filings": {"recent": fixture["filings"]["recent"]}}
    older = fixture["older"]
    events = parse_8k_pages("CRM", "0001234567", [payload, older])
    assert [(event.item_code, event.event_type) for event in events] == [
        ("1.01", "contract_win"),
        ("5.02", "leadership_change"),
        ("2.05", "layoffs_restructuring"),
    ]
    assert events[0].filing_url.endswith("/000123456725000001/contract.htm")
    assert any(event.event_date.isoformat() == "2024-01-04" for event in events)
