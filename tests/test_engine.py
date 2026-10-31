import pytest

from quantmind.memory import HindsightMemory
from quantmind.memory import MemoryRecord, summarize_precedent
from quantmind.models import MarketSnapshot, Report


def test_report_contract_requires_live_snapshot() -> None:
    snapshot = MarketSnapshot(
        asset="PLTR",
        kind="stock",
        price=20,
        change_pct=3,
        history_days=252,
    )
    assert snapshot.asset == "PLTR"


def test_hindsight_can_run_without_cloud_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HINDSIGHT_API_URL", raising=False)
    monkeypatch.delenv("HINDSIGHT_API_TOKEN", raising=False)
    assert HindsightMemory().configured is False


def test_report_disclaimer_is_fixed() -> None:
    assert Report.model_fields["disclaimer"].default == "Research tool, not financial advice."


def test_precedent_extracts_retained_report_event() -> None:
    record = MemoryRecord(
        text=(
            "PLTR moved 6.20% on 2026-09-25. Primary observed driver: contract award.\n"
            "[EVENT] date=2026-09-25 change_pct=6.2000 reason=contract_win forward_5d=unavailable"
        ),
        date=None,
    )
    precedent = summarize_precedent("PLTR", [record])
    assert precedent.count == 1
    assert precedent.moves[0].date == "2026-09-25"
    assert precedent.moves[0].reason == "contract win"


def test_precedent_does_not_infer_unverified_outcome() -> None:
    record = MemoryRecord(
        text=(
            "PLTR moved 18.00% on 2026-09-25. Primary observed driver: contract win.\n"
            "[EVENT] date=2026-09-25 change_pct=18.0000 reason=contract_win forward_5d=unavailable"
        ),
        date=None,
    )
    precedent = summarize_precedent("PLTR", [record])
    assert precedent.moves[0].reason == "contract win"
    assert precedent.moves[0].outcome is None
