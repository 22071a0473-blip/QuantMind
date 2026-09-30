from __future__ import annotations

from dataclasses import dataclass

from .models import SignalView
from .sources import MarketFeatures


@dataclass(frozen=True, slots=True)
class AnalyticsResult:
    signals: list[SignalView]
    group_scores: dict[str, int]
    overall_score: int
    regime: str
    regime_explanation: str
    audit_trail: list[str]

    @property
    def available_count(self) -> int:
        return len(self.signals)


@dataclass(slots=True)
class InstitutionalAnalytics:
    features: MarketFeatures
    memory_count: int

    def calculate(self) -> AnalyticsResult:
        # Every feature is derived from the live provider payload; no placeholder
        # signals are included because an unobservable signal would overstate coverage.
        definitions = [
            ("price_change_1d", self.features.return_1d, 0.10, "yfinance"),
            ("price_change_5d", self.features.return_5d, 0.09, "yfinance"),
            ("price_change_20d", self.features.return_20d, 0.08, "yfinance"),
            ("volatility_20d", self.features.volatility_20d, 0.07, "yfinance"),
            ("volume_ratio", self.features.volume_ratio, 0.10, "yfinance"),
            ("drawdown_1y", self.features.drawdown_1y, 0.07, "yfinance"),
            ("momentum_20d", self.features.momentum_20d, 0.08, "yfinance"),
            ("trend_slope_20d", self.features.trend_slope, 0.08, "yfinance"),
            ("price_vs_sma20", self.features.price_vs_sma20, 0.09, "yfinance"),
            ("price_vs_sma50", self.features.price_vs_sma50, 0.08, "yfinance"),
            ("one_year_range_position", self.features.high_low_position, 0.08, "yfinance"),
            ("news_count", self.features.news_count, 0.08, "yfinance"),
        ]
        signals = [
            SignalView(
                name=name,
                value=round(value, 6),
                weight=weight,
                source=source,
                explanation=f"Observed {name} from {source}; it measures current movement context.",
            )
            for name, value, weight, source in definitions
        ]
        move = self.features.return_1d
        volume = self.features.volume_ratio
        if move >= 1 and volume >= 1.5:
            regime = "catalyst_expansion"
            explanation = "Positive move with abnormal volume indicates information arrival."
        elif move <= -1 and volume >= 1.5:
            regime = "catalyst_stress"
            explanation = "Negative move with abnormal volume indicates stress or negative information."
        else:
            regime = "indeterminate"
            explanation = "Live price and volume do not establish a catalyst regime."
        group_scores = {
            "price_and_volume": self._score(
                [self.features.return_1d, self.features.return_5d, self.features.volume_ratio]
            ),
            "trend_and_risk": self._score(
                [self.features.volatility_20d, self.features.drawdown_1y, self.features.trend_slope]
            ),
            "memory": min(100, 40 + self.memory_count * 12),
        }
        overall = round(sum(group_scores.values()) / len(group_scores))
        audit = [
            "12/12 signals available from live acquisition.",
            f"memory precedent count={self.memory_count}; memory group score={group_scores['memory']}.",
            f"regime={regime}; {explanation}",
        ]
        return AnalyticsResult(
            signals=signals,
            group_scores=group_scores,
            overall_score=overall,
            regime=regime,
            regime_explanation=explanation,
            audit_trail=audit,
        )

    @staticmethod
    def _score(values: list[float]) -> int:
        magnitude = sum(abs(value) for value in values) / max(len(values), 1)
        return max(0, min(100, round(50 + magnitude * 2)))
