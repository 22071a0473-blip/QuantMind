"""SEC Company Facts adapter preserving filing and point-in-time metadata."""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import NAMESPACE_URL, UUID, uuid5

import aiohttp
from pydantic import BaseModel, Field

from .storage import FinancialFactRecord, SQLiteStore


class SecUnitValue(BaseModel):
    val: float
    end: date
    filed: date
    form: str | None = None
    accn: str | None = None
    start: date | None = None
    fy: int | None = None


class SecFactDefinition(BaseModel):
    label: str | None = None
    units: dict[str, list[SecUnitValue]] = Field(default_factory=dict)


class SecCompanyFactsResponse(BaseModel):
    entityName: str
    facts: dict[str, dict[str, SecFactDefinition]] = Field(default_factory=dict)


class NormalizedSecFact(BaseModel):
    taxonomy: str
    fact_name: str
    period_start: date | None
    period_end: date
    filed_at: datetime
    value: float
    unit: str
    form: str | None
    accession: str | None


class SecCompanyFactsProvider:
    name = "sec-companyfacts"
    base_url = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

    def __init__(self, user_agent: str) -> None:
        self.user_agent = user_agent

    async def fetch(self, cik: str) -> list[NormalizedSecFact]:
        normalized_cik = str(cik).zfill(10)
        url = self.base_url.format(cik=normalized_cik)
        headers = {"User-Agent": self.user_agent, "Accept-Encoding": "gzip, deflate"}
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            async with session.get(url) as response:
                response.raise_for_status()
                payload = SecCompanyFactsResponse.model_validate(await response.json())
        records: list[NormalizedSecFact] = []
        for taxonomy, facts in payload.facts.items():
            for fact_name, definition in facts.items():
                for unit, values in definition.units.items():
                    for value in values:
                        available_at = datetime.combine(value.filed, datetime.min.time(), tzinfo=UTC)
                        records.append(
                            NormalizedSecFact(
                                taxonomy=taxonomy,
                                fact_name=fact_name,
                                period_start=value.start,
                                period_end=value.end,
                                filed_at=available_at,
                                value=value.val,
                                unit=unit,
                                form=value.form,
                                accession=value.accn,
                                provider=self.name,
                            )
                        )
        return records


async def persist_company_facts(
    store: SQLiteStore,
    provider: SecCompanyFactsProvider,
    company_id: UUID,
    cik: str,
) -> int:
    facts = await provider.fetch(cik)
    records = [
        FinancialFactRecord(
            fact_id=uuid5(
                NAMESPACE_URL,
                ":".join(
                    (
                        str(company_id),
                        fact.taxonomy,
                        fact.fact_name,
                        fact.period_start.isoformat() if fact.period_start else "",
                        fact.period_end.isoformat(),
                        fact.filed_at.isoformat(),
                        fact.unit,
                        fact.accession or "",
                    )
                ),
            ),
            company_id=company_id,
            taxonomy=fact.taxonomy,
            fact_name=fact.fact_name,
            period_start=fact.period_start,
            period_end=fact.period_end,
            filed_at=fact.filed_at,
            available_at=fact.filed_at,
            value=fact.value,
            unit=fact.unit,
            form=fact.form,
            accession=fact.accession,
            provider=provider.name,
        )
        for fact in facts
    ]
    return store.upsert_financial_facts(records)
