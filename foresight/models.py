from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


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
    patterns: list[str]


class Driver(BaseModel):
    category: str
    probability: float = Field(ge=0, le=1)
    explanation: str
    evidence: list[Evidence]


class DeepResearch(BaseModel):
    company: str
    sector: str
    macro: str


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


class ConfidenceReport(BaseModel):
    score: int = Field(ge=0, le=100)
    signals_available: int = Field(ge=0)
    signals_total: int = Field(ge=1)
    regime: str
    groups: dict[str, int]
    explanation: str
    audit: list[str]


class HistoryReport(BaseModel):
    recalled_patterns: list[str]
    sample_size: int = Field(ge=0)
    limitation: str


class FactsVsReality(BaseModel):
    reported_facts: str
    market_narrative: str
    gap: str
    evidence: list[Evidence]


class Report(BaseModel):
    asset: str
    generated_at: str
    snapshot: MarketSnapshot
    primary_drivers: list[Driver]
    deep_research: DeepResearch
    leadership: LeadershipAssessment
    roadmap: SuccessRoadmap
    confidence: ConfidenceReport
    history: HistoryReport
    facts_vs_reality: FactsVsReality
    memory_used: MemoryUsed
    live_news: list[NewsItem]
    disclaimer: Literal["Research tool, not financial advice."] = (
        "Research tool, not financial advice."
    )
