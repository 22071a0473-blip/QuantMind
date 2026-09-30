"""A dependency-free, typed orchestration state machine."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from .analytics import AnalyticsResult, InstitutionalAnalytics
from .memory import HindsightMemory, RecalledMemory
from .sources import LiveMarketSources, LiveResearchData


class GraphPhase(StrEnum):
    INIT = "init"
    ACQUIRE = "acquire"
    RECALL = "recall"
    ANALYZE = "analyze"
    COMPLETE = "complete"
    FAILED = "failed"


class AgentState(BaseModel):
    asset: str
    query: str = ""
    memory_enabled: bool = True
    phase: GraphPhase = GraphPhase.INIT
    live: LiveResearchData | None = None
    recalled: RecalledMemory | None = None
    analytics: AnalyticsResult | None = None
    errors: list[str] = Field(default_factory=list)


class AgentGraph:
    def __init__(self, sources: LiveMarketSources, memory: HindsightMemory) -> None:
        self.sources = sources
        self.memory = memory

    async def run(self, state: AgentState) -> AgentState:
        current = state.model_copy(deep=True)
        try:
            current.phase = GraphPhase.ACQUIRE
            current.live = await self.sources.gather(current.asset)
            current.phase = GraphPhase.RECALL
            query = current.query or " ".join(item.title for item in current.live.news[:3])
            query = query or f"{current.asset} price volume movement catalyst"
            current.recalled = (
                await self.memory.recall(current.asset, query)
                if current.memory_enabled
                else RecalledMemory(bank_id=self.memory.bank_id(current.asset), records=[], total_count=0)
            )
            current.phase = GraphPhase.ANALYZE
            current.analytics = InstitutionalAnalytics(
                features=current.live.features,
                memory_count=len(current.recalled.records),
            ).calculate()
            current.phase = GraphPhase.COMPLETE
        except Exception as exc:
            current.errors.append(str(exc))
            current.phase = GraphPhase.FAILED
        return current
