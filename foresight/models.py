from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SourceCitation(BaseModel):
    source_type: Literal["news", "sec_filing", "price_data", "macro_data", "memory"]
    source_url: str | None = None
    headline: str | None = None
    date: str


class Evidence(BaseModel):
    source: str
    url: str
    date: str
    snippet: str


class MarketSnapshot(BaseModel):
    asset: str
    kind: Literal["stock", "crypto"]
    price: float
    change_pct: float
    volume_ratio: float | None = None
    market_cap: float | None = None
    history_days: int = Field(ge=1)


class NewsItem(BaseModel):
    title: str
    publisher: str
    url: str
    published: str
    summary: str


class MemoryUsed(BaseModel):
    bank_id: str
    recalled_count: int = Field(ge=0)
    total_count: int = Field(ge=0)
    patterns: list[str]
    backend: Literal["hindsight-cloud"] = "hindsight-cloud"


class Driver(BaseModel):
    category: str
    probability: float = Field(ge=0, le=1)
    explanation: str
    evidence: list[Evidence]
    sources: list[SourceCitation] = Field(default_factory=list)


class DeepResearch(BaseModel):
    company: str
    sector: str
    macro: str
    news: str
    sources: list[SourceCitation] = Field(default_factory=list)


class LeadershipAssessment(BaseModel):
    people: list[str]
    prior_track_record: str
    execution_vs_promises: str
    capital_allocation: str
    governance_and_alignment: str
    evidence_gaps: list[str]
    evidence: list[Evidence]


class RoadmapCondition(BaseModel):
    condition: str
    status: Literal["not_started", "in_progress", "achieved", "at_risk"]
    why_it_matters: str
    evidence: list[Evidence]


class SuccessRoadmap(BaseModel):
    success_definition: str
    required_conditions: list[RoadmapCondition]
    bull_case: str
    base_case: str
    bear_case: str
    kill_conditions: list[str]


class ExtendedAnalysis(BaseModel):
    leadership: LeadershipAssessment
    roadmap: SuccessRoadmap
    note: str = "These sections are speculative and LLM-generated. Treat them as hypotheses, not facts."


class ConfidenceReport(BaseModel):
    score: int = Field(ge=0, le=100)
    signals_available: int = Field(ge=0)
    signals_total: int = Field(ge=1)
    coverage: float = Field(ge=0, le=1)
    regime: str
    groups: dict[str, int]
    explanation: str
    audit: list[str]
    sources: list[SourceCitation] = Field(default_factory=list)


class PrecedentMove(BaseModel):
    date: str
    price_change: float
    reason: str
    follow_through_5d: float | None = None
    source: SourceCitation


class HistoricalPrecedent(BaseModel):
    count: int = Field(ge=0)
    dates: list[str]
    price_changes: list[float]
    reasons: list[str]
    follow_through_5d: list[float | None]
    average_follow_through: float | None
    moves: list[PrecedentMove]
    narrative: str
    meta_insight: str | None = None


class FactsVsReality(BaseModel):
    reported_facts: str
    market_narrative: str
    gap: str
    evidence: list[Evidence]
    sources: list[SourceCitation] = Field(default_factory=list)


class SignalView(BaseModel):
    name: str
    value: float
    weight: float
    source: str
    explanation: str


class SignalResponse(BaseModel):
    ticker: str
    signals: list[SignalView]
    total_signals: int
    confidence_score: int
    coverage: float


class Report(BaseModel):
    asset: str
    generated_at: str
    snapshot: MarketSnapshot
    factor_1_why_it_moved: list[Driver]
    factor_2_deep_research: DeepResearch
    confidence_meter: ConfidenceReport
    historical_precedent: HistoricalPrecedent
    factor_5_facts_vs_reality: FactsVsReality
    extended_analysis: ExtendedAnalysis
    memory_used: MemoryUsed
    live_news: list[NewsItem]
    memory_impact: str | None = None
    warning: str | None = None
    disclaimer: Literal["Research tool, not financial advice."] = (
        "Research tool, not financial advice."
    )
