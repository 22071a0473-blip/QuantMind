import asyncio

from quantmind.agent_graph import AgentGraph, AgentState, GraphPhase
from quantmind.config import Settings
from quantmind.memory import RecalledMemory
from quantmind.models import MarketSnapshot, NewsItem
from quantmind.sources import LiveMarketSources, LiveResearchData, MarketFeatures


def test_settings_reads_typed_environment(monkeypatch) -> None:
    monkeypatch.setenv("QUANTMIND_CACHE_TTL", "17")
    settings = Settings.from_env()
    assert settings.cache_ttl_seconds == 17


def test_graph_state_machine_can_fail_without_sources() -> None:
    class BrokenSources:
        async def gather(self, asset: str):
            raise RuntimeError("provider unavailable")

    class BrokenMemory:
        async def recall(self, asset: str, query: str):
            raise AssertionError("recall should not run")

    state = asyncio.run(AgentGraph(BrokenSources(), BrokenMemory()).run(AgentState(asset="ACME")))
    assert state.phase == GraphPhase.FAILED
    assert "provider unavailable" in state.errors[0]


def test_graph_uses_live_headlines_and_can_skip_memory() -> None:
    class FakeSources(LiveMarketSources):
        async def gather(self, asset: str) -> LiveResearchData:
            return LiveResearchData(
                snapshot=MarketSnapshot(asset=asset, kind="stock", price=10, change_pct=1, history_days=20),
                evidence=[],
                news=[
                    NewsItem(title="Contract award lifts demand", publisher="Wire", url="https://example.com",
                             published="2025-01-01", summary=""),
                ],
                features=MarketFeatures(1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 0.5, 1),
            )

    class FakeMemory:
        def bank_id(self, asset: str) -> str:
            return f"quantmind-{asset.lower()}"

        async def recall(self, asset: str, query: str) -> RecalledMemory:
            raise AssertionError(f"memory should be skipped: {query}")

    state = asyncio.run(
        AgentGraph(FakeSources(), FakeMemory()).run(
            AgentState(asset="ACME", memory_enabled=False)
        )
    )
    assert state.phase == GraphPhase.COMPLETE
    assert state.recalled is not None
    assert state.recalled.records == []
