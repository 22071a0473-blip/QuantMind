import pytest

from foresight.memory import HindsightMemory
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
