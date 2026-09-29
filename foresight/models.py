from typing import Literal

from pydantic import BaseModel, Field


class Evidence(BaseModel):
    source: str
    url: str
    date: str
    snippet: str


class Driver(BaseModel):
    category: Literal[
        "earnings",
        "guidance",
        "contract_deal",
        "macro_fed_rates",
        "regulation_policy",
        "sector_flow",
        "insider_or_whale",
        "product_or_tech",
        "management_change",
        "sentiment",
        "unknown",
    ]
    share: float = Field(ge=0, le=1)
    summary: str
    evidence: list[Evidence]


class Dimension(BaseModel):
    score: int = Field(ge=0, le=100)
    confidence: int = Field(ge=0, le=100)
    notes: str
    evidence: list[Evidence]


class Person(BaseModel):
    name: str
    role: str
    since: str
    dimensions: dict[str, Dimension]


class PromiseLedger(BaseModel):
    total: int = Field(ge=0)
    delivered: int = Field(ge=0)
    missed: int = Field(ge=0)
    pending: int = Field(ge=0)
    items: list[str]


class Leadership(BaseModel):
    overall_grade: str
    people: list[Person]
    promise_ledger: PromiseLedger
    data_gaps: list[str]


class ImpliedRequirements(BaseModel):
    target_price: float = Field(gt=0)
    implied_market_cap: float = Field(gt=0)
    current_market_cap: float = Field(gt=0)
    gap_multiple: float = Field(gt=0)
    assumptions: list[str]


class Condition(BaseModel):
    category: str
    description: str
    status: Literal["not_started", "in_progress", "achieved", "at_risk"]
    evidence: list[Evidence]
    last_updated: str


class Roadmap(BaseModel):
    success_definition: str
    implied_requirements: ImpliedRequirements
    conditions: list[Condition]
    precedents: list[str]
    scenarios: dict[str, str]
    kill_conditions: list[str]


class Confidence(BaseModel):
    score: int = Field(ge=0, le=100)
    groups: dict[str, int]
    explanation: str
    signal_count: int = Field(default=0, ge=0)
    available_signals: int = Field(default=0, ge=0)
    regime: str = "indeterminate"
    audit_trail: list[str] = Field(default_factory=list)


class History(BaseModel):
    cases: list[str]
    n: int = Field(ge=0)
    summary: str


class FactsVsReality(BaseModel):
    reported: str
    market_view: str
    verdict: str
    priced_in: bool


class MemoryItem(BaseModel):
    type: str
    id: str
    summary: str


class Report(BaseModel):
    asset: str
    move: dict[str, float]
    drivers: list[Driver]
    deep_research: dict[str, str]
    leadership: Leadership
    roadmap: Roadmap
    confidence: Confidence
    history: History
    facts_vs_reality: FactsVsReality
    since_last_time: list[str]
    memory_used: list[MemoryItem]
    thesis_check: str | None = None
    disclaimer: Literal["Research tool, not financial advice."] = (
        "Research tool, not financial advice."
    )
