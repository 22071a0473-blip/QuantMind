from __future__ import annotations

import json
from datetime import UTC, datetime

from .analytics import InstitutionalAnalytics
from .llm import GroqResearcher
from .memory import HindsightMemory
from .models import (
    ConfidenceReport,
    DeepResearch,
    FactsVsReality,
    HistoryReport,
    LeadershipAssessment,
    MemoryUsed,
    Report,
    RoadmapCondition,
    SuccessRoadmap,
)
from .sources import LiveMarketSources, LiveResearchData


class QuantMindEngine:
    def __init__(self, memory: HindsightMemory, researcher: GroqResearcher) -> None:
        self._memory = memory
        self._researcher = researcher
        self._sources = LiveMarketSources()

    async def research(self, asset: str, target_price: float | None = None) -> Report:
        live = await self._sources.gather(asset)
        recalled = await self._memory.recall(live.snapshot.asset, "market moves, prior catalysts, leadership, deals, and outcomes")
        analytics = InstitutionalAnalytics(
            price_move_pct=live.snapshot.change_pct,
            volume_vs_average=live.snapshot.volume_ratio or 1,
            sector_move_pct=0,
            memory_count=len(recalled.texts),
            evidence_count=len(live.evidence),
        ).calculate()
        deterministic = Report(
            asset=live.snapshot.asset,
            generated_at=datetime.now(UTC).isoformat(),
            snapshot=live.snapshot,
            primary_drivers=[],
            deep_research=DeepResearch(company="", sector="", macro=""),
            leadership=LeadershipAssessment(
                people=[],
                prior_track_record="Awaiting sourced synthesis.",
                execution_vs_promises="Awaiting sourced synthesis.",
                capital_allocation="Awaiting sourced synthesis.",
                governance_and_alignment="Awaiting sourced synthesis.",
                evidence_gaps=["Leadership records must be retrieved from filings and verified by the synthesis step."],
                evidence=live.evidence,
            ),
            roadmap=SuccessRoadmap(
                success_definition="Awaiting scenario synthesis from live evidence.",
                required_conditions=[],
                bull_case="Awaiting synthesis.",
                base_case="Awaiting synthesis.",
                bear_case="Awaiting synthesis.",
                kill_conditions=[],
            ),
            confidence=ConfidenceReport(
                score=analytics.overall_score,
                signals_available=analytics.available_count,
                signals_total=analytics.signal_count,
                regime=analytics.regime,
                groups=analytics.group_scores,
                explanation=analytics.regime_explanation,
                audit=analytics.audit_trail,
            ),
            history=HistoryReport(
                recalled_patterns=recalled.texts,
                sample_size=len(recalled.texts),
                limitation="Only patterns actually recalled from this Hindsight bank are shown.",
            ),
            facts_vs_reality=FactsVsReality(
                reported_facts="Awaiting sourced synthesis.",
                market_narrative="Awaiting sourced synthesis.",
                gap="Awaiting sourced synthesis.",
                evidence=live.evidence,
            ),
            memory_used=MemoryUsed(
                bank_id=recalled.bank_id,
                recalled_count=len(recalled.texts),
                patterns=recalled.texts,
            ),
            live_news=live.news,
        )
        report = await self._researcher.synthesize(
            live.snapshot.asset,
            json.dumps({"snapshot": live.snapshot.model_dump(), "evidence": [item.model_dump() for item in live.evidence], "news": [item.model_dump() for item in live.news]}),
            "\n".join(recalled.texts),
            deterministic.model_dump_json(),
        )
        if target_price is not None:
            report.roadmap.success_definition += f" Target-price scenario input: {target_price:.4f}; this is not a prediction."
        await self._memory.retain(live.snapshot.asset, report.model_dump_json())
        return report
