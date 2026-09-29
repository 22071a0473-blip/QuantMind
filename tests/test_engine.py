import pytest

from foresight.memory import HindsightMemory
from foresight.memory import MemoryRecord, summarize_precedent
from foresight.models import MarketSnapshot, Report


def test_report_contract_requires_live_snapshot() -> None:
    snapshot = MarketSnapshot(
        asset="PLTR",
        kind="stock",
        price=20,
        change_pct=3,
        history_days=252,
    )
    assert snapshot.asset == "PLTR"


def test_hindsight_requires_cloud_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HINDSIGHT_API_URL", raising=False)
    monkeypatch.delenv("HINDSIGHT_API_TOKEN", raising=False)
    with pytest.raises(KeyError):
        HindsightMemory()


def test_report_disclaimer_is_fixed() -> None:
    assert Report.model_fields["disclaimer"].default == "Research tool, not financial advice."


def test_precedent_extracts_retained_report_event() -> None:
    record = MemoryRecord(
        text='{"generated_at":"2026-09-25T12:00:00Z","snapshot":{"change_pct":6.2},"factor_1_why_it_moved":[{"category":"Contract"}]}',
        date=None,
    )
    precedent = summarize_precedent("PLTR", [record])
    assert precedent.count == 1
    assert precedent.moves[0].date == "2026-09-25"
    assert precedent.moves[0].reason == "Contract"


def test_precedent_extracts_seeded_thesis_outcome() -> None:
    record = MemoryRecord(
        text=(
            '{"generated_at":"2026-09-25","snapshot":{"change_pct":18},'
            '"factor_1_why_it_moved":[{"category":"DoD AI TITAN Contract Win"}],'
            '"memory_thesis":{"outcome":"+18% over 30 days"}}'
        ),
        date=None,
    )
    precedent = summarize_precedent("PLTR", [record])
    assert precedent.moves[0].reason == "DoD AI TITAN Contract Win"
    assert precedent.moves[0].outcome == "+18% over 30 days"


def test_demo_seed_preview_provides_pltr_precedents() -> None:
    records = HindsightMemory._demo_records("PLTR")
    precedent = summarize_precedent("PLTR", records)
    assert precedent.count == 2
    assert precedent.moves[0].outcome == "+18% over 30 days"
