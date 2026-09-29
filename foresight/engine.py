from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime

from .analytics import AnalyticsResult, InstitutionalAnalytics
from .llm import GroqResearcher
from .memory import HindsightMemory, RecalledMemory, summarize_precedent
from .models import (
    ConfidenceReport,
    DeepResearch,
    Driver,
    ExtendedAnalysis,
    FactsVsReality,
    HistoricalPrecedent,
    LeadershipAssessment,
    MemoryUsed,
    Report,
    SuccessRoadmap,
)
from .sources import LiveMarketSources, LiveResearchData


@dataclass(slots=True)
class ResearchResult:
    report: Report
    analytics: AnalyticsResult


class QuantMindEngine:
    def __init__(self, memory: HindsightMemory, researcher: GroqResearcher) -> None:
        self._memory = memory
        self._researcher = researcher
        self._sources = LiveMarketSources()

    async def reflect(self, asset: str, query: str) -> str:
        return await self._memory.reflect(asset, query)

    async def list_memory_bank(self, asset: str) -> dict[str, object]:
        return await self._memory.list_memories(asset)

    async def signal_snapshot(self, asset: str) -> AnalyticsResult:
        live = await self._sources.gather(asset)
        recalled = await self._memory.recall(asset, f"{asset} historical market patterns")
        return InstitutionalAnalytics(
            features=live.features,
            memory_count=len(recalled.records),
        ).calculate()

    async def research(self, asset: str, memory_enabled: bool = True) -> ResearchResult:
        live = await self._sources.gather(asset)
        recalled = (
            await self._memory.recall(
                live.snapshot.asset,
                f"{live.snapshot.asset} moved {live.snapshot.change_pct:.2f}% primary reason Unclassified sector market",
            )
            if memory_enabled
            else RecalledMemory(bank_id=self._memory.bank_id(live.snapshot.asset), records=[], total_count=0)
        )
        precedent = summarize_precedent(live.snapshot.asset, recalled.records, recalled.meta_insight)
        analytics = InstitutionalAnalytics(
            features=live.features,
            memory_count=precedent.count if memory_enabled else 0,
        ).calculate()
        deterministic = self._deterministic_report(live, recalled, precedent, analytics, memory_enabled)
        try:
            report = await self._researcher.synthesize(
                live.snapshot.asset,
                json.dumps(
                    {
                        "snapshot": live.snapshot.model_dump(),
                        "evidence": [item.model_dump() for item in live.evidence],
                        "news": [item.model_dump() for item in live.news],
                    }
                ),
                "\n".join(recalled.texts),
                deterministic,
            )
        except Exception as exc:
            deterministic.warning = f"Groq synthesis unavailable: {exc}"
            report = deterministic
        report.historical_precedent = precedent
        report.confidence_meter = deterministic.confidence_meter
        if memory_enabled and precedent.count:
            report.memory_impact = (
                f"Hindsight memory improved this report. Without it, Factor 4 would be empty and "
                f"confidence would be {max(0, deterministic.confidence_meter.score - 12)} points lower."
            )
        primary_reason = report.factor_1_why_it_moved[0].category if report.factor_1_why_it_moved else "Unclassified"
        total = await self._memory.retain(
            live.snapshot.asset,
            report.model_dump_json(),
            live.snapshot.change_pct,
            primary_reason,
        )
        report.memory_used.total_count = total
        if total > 0 and total % 5 == 0:
            insight = await self._memory.reflect(
                live.snapshot.asset,
                "What patterns emerge from this ticker's historical moves?",
            )
            await self._memory.retain_insight(live.snapshot.asset, insight, total)
            report.historical_precedent.meta_insight = insight
        return ResearchResult(report=report, analytics=analytics)

    @staticmethod
    def _deterministic_report(
        live: LiveResearchData,
        recalled: RecalledMemory,
        precedent: HistoricalPrecedent,
        analytics: AnalyticsResult,
        memory_enabled: bool,
    ) -> Report:
        date = datetime.now(UTC).date().isoformat()
        source = live.evidence
        driver = Driver(
            category="Unclassified" if not live.news else "Market news and price/volume response",
            probability=0.2 if not live.news else 0.55,
            explanation=(
                "No news source was returned; the move is unclassified and confidence is lower."
                if not live.news
                else "Live news and the price/volume response are the available catalyst evidence."
            ),
            evidence=source,
        )
        leadership = LeadershipAssessment(
            people=[],
            prior_track_record="insufficient evidence",
            execution_vs_promises="insufficient evidence",
            capital_allocation="insufficient evidence",
            governance_and_alignment="insufficient evidence",
            evidence_gaps=["Leadership and board evidence requires verified filings in the supplied sources."],
            evidence=source,
        )
        roadmap = SuccessRoadmap(
            success_definition="insufficient evidence for a company-specific success definition",
            required_conditions=[],
            bull_case="insufficient evidence",
            base_case="insufficient evidence",
            bear_case="insufficient evidence",
            kill_conditions=[],
        )
        return Report(
            asset=live.snapshot.asset,
            generated_at=datetime.now(UTC).isoformat(),
            snapshot=live.snapshot,
            factor_1_why_it_moved=[driver],
            factor_2_deep_research=DeepResearch(
                company="insufficient evidence",
                sector="insufficient evidence",
                macro="insufficient evidence",
                news="No news found." if not live.news else f"{len(live.news)} live news items returned.",
            ),
            confidence_meter=ConfidenceReport(
                score=max(0, analytics.overall_score - (0 if memory_enabled else 12)),
                signals_available=len(analytics.signals),
                signals_total=len(analytics.signals),
                coverage=1.0,
                regime=analytics.regime,
                groups=analytics.group_scores,
                explanation=analytics.regime_explanation,
                audit=analytics.audit_trail,
            ),
            historical_precedent=precedent,
            factor_5_facts_vs_reality=FactsVsReality(
                reported_facts="Only the live provider evidence is treated as fact.",
                market_narrative="insufficient evidence",
                gap="insufficient evidence",
                evidence=source,
            ),
            extended_analysis=ExtendedAnalysis(leadership=leadership, roadmap=roadmap),
            memory_used=MemoryUsed(
                bank_id=recalled.bank_id,
                recalled_count=precedent.count if memory_enabled else 0,
                total_count=recalled.total_count,
                patterns=recalled.texts,
            ),
            live_news=live.news,
        )
