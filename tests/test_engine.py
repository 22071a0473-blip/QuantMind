import pytest

from foresight.engine import build_report
from foresight.memory import MemoryService


@pytest.mark.asyncio
async def test_report_is_schema_validated_and_exposes_memory(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HINDSIGHT_API_URL", raising=False)
    monkeypatch.delenv("HINDSIGHT_API_TOKEN", raising=False)
    report = await build_report("PLTR", 40, MemoryService())

    assert report.asset == "PLTR"
    assert len(report.drivers) == 1
    assert report.roadmap.implied_requirements.gap_multiple > 1
    assert report.disclaimer == "Research tool, not financial advice."
    assert {item.type for item in report.memory_used} == {"company_dossier", "promise_ledger"}
    assert report.confidence.signal_count >= 30
    assert report.confidence.available_signals < report.confidence.signal_count
    assert report.confidence.regime == "catalyst_expansion"


@pytest.mark.asyncio
async def test_memory_round_trip_is_visible(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HINDSIGHT_API_URL", raising=False)
    monkeypatch.delenv("HINDSIGHT_API_TOKEN", raising=False)
    memory = MemoryService()
    await memory.retain("PLTR", "A milestone changed.")

    report = await build_report("PLTR", 40, memory)

    assert any(item.type == "historical_memory" for item in report.memory_used)
