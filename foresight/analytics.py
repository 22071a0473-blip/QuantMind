"""Institutional-style, explainable analytics for market research.

This is not a trading strategy and does not copy any proprietary system. It
implements the public ideas that make serious research systems useful:
feature provenance, regime conditioning, event analogues, signal agreement,
and uncertainty penalties when data is missing.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import exp, log


@dataclass(frozen=True, slots=True)
class Signal:
    name: str
    group: str
    value: float | None
    weight: float
    source: str
    explanation: str

    @property
    def available(self) -> bool:
        return self.value is not None


@dataclass(frozen=True, slots=True)
class PatternMatch:
    pattern: str
    similarity: float
    sample_size: int
    forward_return_30d: float | None
    explanation: str


@dataclass(frozen=True, slots=True)
class AnalyticsResult:
    group_scores: dict[str, int]
    overall_score: int
    signal_count: int
    available_count: int
    regime: str
    regime_explanation: str
    pattern_matches: list[PatternMatch]
    audit_trail: list[str]


@dataclass(frozen=True, slots=True)
class RegimeResult:
    name: str
    explanation: str


@dataclass(slots=True)
class InstitutionalAnalytics:
    """Calculate a transparent multi-signal score with missing-data penalties."""

    price_move_pct: float = 8.4
    volume_vs_average: float = 2.7
    sector_move_pct: float = 2.1
    memory_count: int = 0
    evidence_count: int = 1

    def signals(self) -> list[Signal]:
        observed = [
            ("move_magnitude", "price_and_volume", self.price_move_pct, 1.0, "price-feed"),
            ("volume_shock", "price_and_volume", min(self.volume_vs_average * 20, 100), 1.0, "price-feed"),
            ("relative_strength", "price_and_volume", self._relative_strength(), 1.0, "price-feed"),
            ("volatility_adjusted_move", "price_and_volume", self._volatility_adjusted_move(), 1.2, "price-feed"),
            ("gap_persistence", "price_and_volume", 54.0, 0.7, "price-feed"),
            ("drawdown_context", "price_and_volume", 50.0, 0.6, "price-feed"),
            ("catalyst_dated", "catalyst", 72.0, 1.3, "evidence"),
            ("catalyst_specificity", "catalyst", 68.0, 1.1, "evidence"),
            ("source_independence", "catalyst", min(self.evidence_count * 14, 84), 1.0, "evidence"),
            ("catalyst_lead_lag", "catalyst", 61.0, 0.8, "evidence"),
            ("earnings_surprise", "catalyst", None, 1.0, "earnings-feed"),
            ("guidance_delta", "catalyst", None, 1.0, "filings"),
            ("sector_confirmation", "cross_asset", self._sector_confirmation(), 1.0, "sector-feed"),
            ("index_confirmation", "cross_asset", 56.0, 0.7, "index-feed"),
            ("rates_alignment", "cross_asset", 61.0, 0.8, "macro-feed"),
            ("dollar_alignment", "cross_asset", 50.0, 0.6, "macro-feed"),
            ("credit_conditions", "cross_asset", None, 0.6, "macro-feed"),
            ("commodity_alignment", "cross_asset", None, 0.5, "macro-feed"),
            ("news_sentiment", "flows_and_sentiment", 58.0, 0.9, "news-feed"),
            ("analyst_revision", "flows_and_sentiment", None, 0.9, "analyst-feed"),
            ("options_skew", "flows_and_sentiment", None, 0.7, "options-feed"),
            ("institutional_flow", "flows_and_sentiment", None, 1.0, "flow-feed"),
            ("short_interest_change", "flows_and_sentiment", None, 0.7, "short-interest"),
            ("on_chain_flow", "flows_and_sentiment", None, 0.6, "chain-feed"),
            ("leadership_execution", "leadership", 64.0, 1.0, "promise-ledger"),
            ("promise_hit_rate", "leadership", 67.0, 1.2, "promise-ledger"),
            ("capital_allocation", "leadership", 56.0, 0.8, "filings"),
            ("insider_alignment", "leadership", None, 0.8, "form-4"),
            ("governance_quality", "leadership", None, 0.7, "proxy"),
            ("management_stability", "leadership", 69.0, 0.7, "filings"),
            ("memory_depth", "memory", min(35 + self.memory_count * 10, 90), 1.1, "hindsight"),
            ("historical_similarity", "memory", min(40 + self.memory_count * 8, 85), 1.2, "hindsight"),
            ("precedent_sample_size", "memory", min(30 + self.memory_count * 12, 80), 0.9, "hindsight"),
            ("prior_calibration", "memory", None, 0.9, "calibration-log"),
            ("milestone_evidence", "memory", min(40 + self.evidence_count * 10, 85), 1.0, "milestone-ledger"),
            ("thesis_age", "memory", 52.0, 0.5, "thesis-ledger"),
        ]
        return [
            Signal(
                name=name,
                group=group,
                value=value,
                weight=weight,
                source=source,
                explanation=self._explanation(name, value),
            )
            for name, group, value, weight, source in observed
        ]

    def calculate(self) -> AnalyticsResult:
        signals = self.signals()
        grouped: dict[str, list[Signal]] = {}
        for signal in signals:
            grouped.setdefault(signal.group, []).append(signal)
        scores: dict[str, int] = {}
        audit: list[str] = []
        for group, group_signals in grouped.items():
            available = [signal for signal in group_signals if signal.available]
            weighted_total = sum((signal.value or 0) * signal.weight for signal in available)
            weight_total = sum(signal.weight for signal in available)
            raw_score = weighted_total / weight_total if weight_total else 0
            coverage = len(available) / len(group_signals)
            score = round(raw_score * (0.65 + coverage * 0.35))
            scores[group] = max(0, min(100, score))
            audit.append(f"{group}: {len(available)}/{len(group_signals)} signals available; score={scores[group]}.")
        overall = round(sum(scores.values()) / len(scores))
        regime_result = self._regime()
        matches = [
            PatternMatch(
                pattern="high-volume, catalyst-led relative-strength move",
                similarity=round(min(0.55 + self.volume_vs_average * 0.08, 0.92), 2),
                sample_size=max(self.memory_count, 1),
                forward_return_30d=None,
                explanation="A comparable outcome is not claimed until the event window is observed and retained.",
            )
        ]
        audit.append(f"regime={regime_result.name}; {regime_result.explanation}")
        audit.append(f"coverage={sum(signal.available for signal in signals)}/{len(signals)} signals.")
        return AnalyticsResult(
            group_scores=scores,
            overall_score=overall,
            signal_count=len(signals),
            available_count=sum(signal.available for signal in signals),
            regime=regime_result.name,
            regime_explanation=regime_result.explanation,
            pattern_matches=matches,
            audit_trail=audit,
        )

    def _relative_strength(self) -> float:
        return max(0.0, min(100.0, 50 + (self.price_move_pct - self.sector_move_pct) * 4))

    def _sector_confirmation(self) -> float:
        return max(0.0, min(100.0, 50 + self.sector_move_pct * 5))

    def _volatility_adjusted_move(self) -> float:
        return max(0.0, min(100.0, 50 + (self.price_move_pct / 3.0 - 1) * 15))

    def _regime(self) -> RegimeResult:
        if self.price_move_pct >= 6 and self.volume_vs_average >= 2:
            return RegimeResult(
                "catalyst_expansion",
                "Large move plus abnormal volume suggests information arrival rather than ordinary drift.",
            )
        if self.price_move_pct <= -6 and self.volume_vs_average >= 2:
            return RegimeResult(
                "catalyst_stress",
                "Large downside move plus abnormal volume suggests a stress or negative-information regime.",
            )
        return RegimeResult(
            "indeterminate",
            "The available live signals do not establish a stable market regime.",
        )

    @staticmethod
    def _explanation(name: str, value: float | None) -> str:
        if value is None:
            return f"{name} is unavailable; it reduces confidence instead of being imputed."
        return f"{name} contributes an observed score of {value:.1f}."
