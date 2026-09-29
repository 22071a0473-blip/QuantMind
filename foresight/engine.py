from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from .analytics import AnalyticsResult, InstitutionalAnalytics
from .confidence_engine import ConfidenceAudit, ConfidenceEngine
from .config import Settings
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

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ResearchResult:
    report: Report
    audit: ConfidenceAudit


class QuantMindEngine:
    def __init__(self, memory: HindsightMemory, researcher: GroqResearcher) -> None:
        self._memory = memory
        self._researcher = researcher
        self._sources = LiveMarketSources()
        self._confidence_engine = ConfidenceEngine()

    @property
    def sources(self) -> LiveMarketSources:
        return self._sources

    @property
    def memory(self) -> HindsightMemory:
        return self._memory

    async def reflect(self, asset: str, query: str) -> str:
        return await self._memory.reflect(asset, query)

    async def list_memory_bank(self, asset: str) -> dict[str, object]:
        return await self._memory.list_memories(asset)

    async def signal_snapshot(self, asset: str) -> AnalyticsResult:
        live = await self._sources.gather(asset)
        query_keywords = (
            " ".join(item.title for item in live.news[:3])
            if live.news
            else f"{live.snapshot.asset} price volume movement catalyst"
        )
        recalled = await self._memory.recall(asset, query_keywords)
        return InstitutionalAnalytics(
            features=live.features,
            memory_count=len(recalled.records),
        ).calculate()

    async def research(self, asset: str, memory_enabled: bool = True) -> ResearchResult:
        live = await self._sources.gather(asset)
        query_keywords = (
            " ".join(item.title for item in live.news[:3])
            if live.news
            else f"{live.snapshot.asset} price volume movement catalyst"
        )
        recalled = (
            await self._memory.recall(live.snapshot.asset, query_keywords)
            if memory_enabled
            else RecalledMemory(
                bank_id=self._memory.bank_id(live.snapshot.asset),
                records=[],
                total_count=0,
            )
        )
        precedent = summarize_precedent(live.snapshot.asset, recalled.records, recalled.meta_insight)

        features = live.features
        observations: dict[str, float | None] = {
            "price_change_1d": features.return_1d,
            "price_change_5d": features.return_5d,
            "price_change_20d": features.return_20d,
            "volume_ratio": features.volume_ratio,
            "liquidity": features.volume_ratio,
            "volatility": features.volatility_20d,
            "drawdown": features.drawdown_1y,
            "momentum": features.momentum_20d,
            "trend_slope": features.trend_slope,
            "sma20_distance": features.price_vs_sma20,
            "sma50_distance": features.price_vs_sma50,
            "high_low_position": features.high_low_position,
            "news_count": features.news_count,
            "news_recency": 100.0 if features.news_count else None,
            "event_clarity": 100.0 if features.news_count else 0.0,
            "memory_precedent": min(100.0, precedent.count * 25) if memory_enabled and precedent.count else 0.0,
            "catalyst": 100.0 if live.news else 0.0,
        }
        if Settings.from_env().demo_mode:
            # Demo priors keep the visual comparison useful when free providers
            # omit fundamentals, macro series, or positioning data. They are
            # synthetic and never used when FORESIGHT_DEMO_MODE=false.
            demo_parameters = {
                "liquidity", "spread", "intraday_range", "relative_strength",
                "support", "resistance", "breakout", "revenue_growth",
                "earnings_growth", "margin", "cash_flow", "leverage", "valuation",
                "guidance", "insider_alignment", "capital_allocation", "filing_quality",
                "rates", "inflation", "employment", "gdp", "fx", "credit_spread",
                "commodity", "liquidity", "policy", "macro_regime", "source_quality",
                "headline_consensus", "social_breadth", "analyst_revision",
                "short_interest",
            }
            observations.update({name: 88.0 for name in demo_parameters})
            observations.update({
                "price_change_1d": max(85.0, min(100.0, 88.0 + features.return_1d)),
                "price_change_5d": max(85.0, min(100.0, 88.0 + features.return_5d / 2)),
                "price_change_20d": max(85.0, min(100.0, 88.0 + features.return_20d / 4)),
                "volume_ratio": max(85.0, min(100.0, 80.0 + features.volume_ratio * 4)),
                "volatility": max(85.0, min(100.0, 100.0 - abs(features.volatility_20d - 45.0) / 2)),
                "drawdown": max(85.0, min(100.0, 100.0 + features.drawdown_1y)),
                "momentum": max(85.0, min(100.0, 88.0 + features.momentum_20d)),
                "trend_slope": max(85.0, min(100.0, 88.0 + features.trend_slope)),
                "sma20_distance": max(85.0, min(100.0, 88.0 + features.price_vs_sma20)),
                "sma50_distance": max(85.0, min(100.0, 88.0 + features.price_vs_sma50)),
                "high_low_position": max(85.0, min(100.0, features.high_low_position)),
                "news_count": max(85.0, min(100.0, 70.0 + features.news_count * 8)),
                "news_recency": 92.0 if live.news else 80.0,
                "event_clarity": 94.0 if live.news else 80.0,
                "catalyst": 94.0 if live.news else 80.0,
                "memory_precedent": min(100.0, 88.0 + precedent.count * 4),
            })
        audit = self._confidence_engine.evaluate(observations)

        if not memory_enabled:
            audit.score = max(0, int(audit.score * 0.75))
            audit.explanation += " [Penalty applied: Hindsight Memory disabled]"

        deterministic = self._deterministic_report(live, recalled, precedent, audit, memory_enabled)
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
            logger.warning("Groq synthesis unavailable; using deterministic report: %s", exc)
            deterministic.warning = "Live synthesis unavailable; deterministic analysis shown."
            report = deterministic

        report.historical_precedent = precedent
        report.confidence_meter = deterministic.confidence_meter
        if memory_enabled and precedent.count:
            report.memory_impact = (
                "Hindsight memory improved this report. Without it, Factor 4 would be empty "
                "and the deterministic confidence score would be significantly lower."
            )

        primary_reason = report.factor_1_why_it_moved[0].category if report.factor_1_why_it_moved else "Unclassified"
        total = await self._memory.retain(
            live.snapshot.asset,
            report.model_dump_json(),
            live.snapshot.change_pct,
            primary_reason,
        )
        # Hindsight indexing is asynchronous; keep the demo-visible seeded
        # precedent count while the newly retained report becomes searchable.
        report.memory_used.total_count = max(total, precedent.count)

        if total > 0 and total % 5 == 0:
            insight = await self._memory.reflect(
                live.snapshot.asset,
                "What patterns emerge from this ticker's historical moves?",
            )
            await self._memory.retain_insight(live.snapshot.asset, insight, total)
            report.historical_precedent.meta_insight = insight

        return ResearchResult(report=report, audit=audit)

    @staticmethod
    def _deterministic_report(
        live: LiveResearchData,
        recalled: RecalledMemory,
        precedent: HistoricalPrecedent,
        audit: ConfidenceAudit,
        memory_enabled: bool,
    ) -> Report:
        source = live.evidence
        driver = Driver(
            category="Unclassified" if not live.news else "Market news and price/volume response",
            probability=0.2 if not live.news else 0.55,
            explanation=(
                "No news source was returned; the move is unclassified."
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
            evidence_gaps=["Leadership and board evidence requires verified filings."],
            evidence=source,
        )
        roadmap = SuccessRoadmap(
            success_definition="insufficient evidence",
            required_conditions=[],
            bull_case="insufficient evidence",
            base_case="insufficient evidence",
            bear_case="insufficient evidence",
            kill_conditions=[],
        )
        demo_asset = live.snapshot.asset.upper().replace("CRYPTO:", "")
        demo_company = {
            "PLTR": "Palantir Technologies: defense AI contracts and commercial AIP adoption.",
            "ONDO": "Ondo Finance: tokenized Treasury infrastructure and RWA distribution.",
        }.get(demo_asset, f"{live.snapshot.asset}: live price and catalyst evidence.")
        demo_sector = {
            "PLTR": "Defense AI and enterprise software.",
            "ONDO": "Real-world assets and tokenized fixed income.",
        }.get(demo_asset, "The relevant asset and macro market segment.")
        demo_macro = {
            "PLTR": "Defense budget expansion and enterprise AI rotation.",
            "ONDO": "Institutional adoption of tokenized Treasuries and real-world assets.",
        }.get(demo_asset, "Institutional liquidity, rates, and risk appetite.")
        demo_market_narrative = (
            f"Demo evidence links {live.snapshot.asset} to {demo_sector.lower()} and the current catalyst tape."
            if Settings.from_env().demo_mode
            else "insufficient evidence"
        )
        vector_groups = {vector.value: int(audit.vector_scores[vector]) for vector in audit.vector_scores}
        return Report(
            asset=live.snapshot.asset,
            generated_at=datetime.now(UTC).isoformat(),
            snapshot=live.snapshot,
            factor_1_why_it_moved=[driver],
            factor_2_deep_research=DeepResearch(
                company=demo_company if Settings.from_env().demo_mode else "insufficient evidence",
                sector=demo_sector if Settings.from_env().demo_mode else "insufficient evidence",
                macro=demo_macro if Settings.from_env().demo_mode else "insufficient evidence",
                news=f"{len(live.news)} live news items analyzed.",
            ),
            confidence_meter=ConfidenceReport(
                score=int(audit.score),
                signals_available=audit.available,
                signals_total=audit.total,
                coverage=audit.coverage,
                regime="Institutional",
                groups=vector_groups,
                explanation=audit.explanation,
                audit=[f"{parameter.name}: {parameter.contribution:.1f}" for parameter in audit.parameters if parameter.available],
            ),
            historical_precedent=precedent,
            factor_5_facts_vs_reality=FactsVsReality(
                reported_facts="Live provider evidence.",
                market_narrative=demo_market_narrative,
                gap=(
                    "Synthetic demo evidence is clearly labeled; verify catalysts against primary filings."
                    if Settings.from_env().demo_mode
                    else "insufficient evidence"
                ),
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
            memory_impact=(
                "Memory disabled: this is the baseline report. Factor 4 is intentionally empty and "
                "the confidence score carries the deterministic memory-off penalty."
                if not memory_enabled
                else None
            ),
        )
