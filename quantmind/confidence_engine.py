"""Deterministic confidence scoring with explicit missing-data accounting."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, Field

from .utils import clamp


class ConfidenceVector(StrEnum):
    MARKET = "market"
    TECHNICAL = "technical"
    FUNDAMENTAL = "fundamental"
    MACRO = "macro"
    SENTIMENT = "sentiment"


@dataclass(frozen=True, slots=True)
class Parameter:
    name: str
    vector: ConfidenceVector
    weight: float


def _parameters() -> tuple[Parameter, ...]:
    names = (
        ("market", ("price_change_1d", "price_change_5d", "price_change_20d", "volume_ratio", "liquidity",
                    "market_cap", "price_history", "spread", "intraday_range", "relative_strength")),
        ("technical", ("volatility", "drawdown", "momentum", "trend_slope", "sma20_distance", "sma50_distance",
                       "high_low_position", "support", "resistance", "breakout")),
        ("fundamental", ("revenue_growth", "earnings_growth", "margin", "cash_flow", "leverage", "valuation",
                         "guidance", "insider_alignment", "capital_allocation", "filing_quality")),
        ("macro", ("rates", "inflation", "employment", "gdp", "fx", "credit_spread", "commodity", "liquidity",
                   "policy", "macro_regime")),
        ("sentiment", ("news_count", "news_recency", "source_quality", "headline_consensus", "catalyst",
                       "social_breadth", "analyst_revision", "short_interest", "memory_precedent", "event_clarity")),
    )
    items: list[Parameter] = []
    for vector_name, vector_names in names:
        vector = ConfidenceVector(vector_name)
        items.extend(Parameter(name=name, vector=vector, weight=0.02) for name in vector_names)
    return tuple(items)


CONFIDENCE_PARAMETERS = _parameters()
VECTOR_WEIGHTS: dict[ConfidenceVector, float] = {
    vector: 0.2 for vector in ConfidenceVector
}


class ParameterAudit(BaseModel):
    name: str
    vector: ConfidenceVector
    value: float | None = Field(default=None, ge=0, le=100)
    available: bool
    contribution: float = Field(ge=0, le=100)


class ConfidenceAudit(BaseModel):
    score: float = Field(ge=0, le=100)
    coverage: float = Field(ge=0, le=1)
    available: int = Field(ge=0)
    total: int = Field(ge=1)
    vector_scores: dict[ConfidenceVector, float]
    parameters: list[ParameterAudit]
    missing: list[str]
    explanation: str


class ConfidenceEngine:
    """Score normalized observations; absent observations never become fake zeros."""

    parameters = CONFIDENCE_PARAMETERS
    vector_weights = VECTOR_WEIGHTS

    def evaluate(self, observations: dict[str, float | None]) -> ConfidenceAudit:
        audits: list[ParameterAudit] = []
        missing: list[str] = []
        vector_values: dict[ConfidenceVector, list[float]] = {vector: [] for vector in ConfidenceVector}
        for parameter in self.parameters:
            raw = observations.get(parameter.name)
            value = clamp(float(raw)) if raw is not None else None
            if value is None:
                missing.append(parameter.name)
                contribution = 0.0
            else:
                vector_values[parameter.vector].append(value)
                contribution = value * parameter.weight
            audits.append(ParameterAudit(name=parameter.name, vector=parameter.vector, value=value,
                                         available=value is not None, contribution=contribution))
        vector_scores = {
            vector: round(sum(values) / len(values), 4) if values else 0.0
            for vector, values in vector_values.items()
        }
        score = sum(vector_scores[vector] * weight for vector, weight in self.vector_weights.items())
        available = len(self.parameters) - len(missing)
        coverage = available / len(self.parameters)
        return ConfidenceAudit(
            score=round(clamp(score), 4),
            coverage=coverage,
            available=available,
            total=len(self.parameters),
            vector_scores=vector_scores,
            parameters=audits,
            missing=missing,
            explanation=f"{available}/{len(self.parameters)} deterministic parameters available.",
        )

