"""Versioned Fortune 500 ingestion and company-to-security resolution."""

from __future__ import annotations

import csv
import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from typing import Protocol
from uuid import NAMESPACE_URL, uuid5

from pydantic import BaseModel

from .storage import CompanyRecord, DataSourceRecord, SecurityRecord, SQLiteStore
from .universe import UniverseAsset


class Fortune500Row(BaseModel):
    rank: int
    company_name: str
    ticker: str | None = None
    exchange: str | None = None
    headquarters: str | None = None
    website: str | None = None


class Fortune500Provider(Protocol):
    name: str
    source_url: str

    def fetch(self, ranking_year: int) -> list[Fortune500Row]: ...


class CsvFortune500Provider:
    """Read a provider-exported CSV with stable, documented column aliases."""

    name = "fortune500-csv"

    def __init__(self, source: Path | str) -> None:
        self.source = source
        self.source_url = str(source)

    def fetch(self, ranking_year: int) -> list[Fortune500Row]:
        del ranking_year
        if isinstance(self.source, Path):
            payload = self.source.read_text(encoding="utf-8-sig")
        else:
            payload = self.source
        rows = csv.DictReader(StringIO(payload))
        return [
            Fortune500Row(
                rank=int(_required(row, "rank", "rank_order", "fortune_rank")),
                company_name=_required(row, "company", "company_name", "name"),
                ticker=_optional(row, "ticker", "symbol"),
                exchange=_optional(row, "exchange"),
                headquarters=_optional(row, "headquarters", "hq"),
                website=_optional(row, "website", "url"),
            )
            for row in rows
        ]


def _required(row: dict[str, str], *names: str) -> str:
    for name in names:
        value = row.get(name)
        if value and value.strip():
            return value.strip()
    raise ValueError(f"CSV row is missing one of: {', '.join(names)}")


def _optional(row: dict[str, str], *names: str) -> str | None:
    for name in names:
        value = row.get(name)
        if value and value.strip():
            return value.strip()
    return None


def normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def resolve_security(row: Fortune500Row, assets: Iterable[UniverseAsset]) -> UniverseAsset | None:
    candidates = {asset.symbol: asset for asset in assets}
    if row.ticker:
        symbol = row.ticker.strip().upper().replace(".", "-")
        if symbol in candidates:
            return candidates[symbol]
    target = normalize_name(row.company_name)
    matches = [
        asset
        for asset in candidates.values()
        if normalize_name(asset.name) == target or target in {normalize_name(alias) for alias in asset.aliases}
    ]
    return matches[0] if len(matches) == 1 else None


@dataclass(frozen=True, slots=True)
class UniverseIngestionReport:
    ranking_year: int
    discovered_companies: int
    resolved_securities: int
    unresolved_companies: list[str]
    source_url: str
    retrieved_at: datetime


def ingest_fortune500(
    store: SQLiteStore,
    provider: Fortune500Provider,
    ranking_year: int,
    assets: Iterable[UniverseAsset],
) -> UniverseIngestionReport:
    rows = provider.fetch(ranking_year)
    asset_list = list(assets)
    unresolved: list[str] = []
    resolved = 0
    retrieved_at = datetime.now(UTC)
    store.upsert_source(
        DataSourceRecord(
            source_id=uuid5(NAMESPACE_URL, f"quantmind:source:{provider.name}:{ranking_year}:{provider.source_url}"),
            provider=provider.name,
            source_url=provider.source_url,
            retrieved_at=retrieved_at,
        )
    )
    for row in rows:
        company_id = uuid5(NAMESPACE_URL, f"quantmind:fortune500:{ranking_year}:{normalize_name(row.company_name)}")
        asset = resolve_security(row, asset_list)
        company = CompanyRecord(
            company_id=company_id,
            legal_name=row.company_name,
            fortune_rank_year=ranking_year,
            fortune_rank=row.rank,
            sector=asset.sector if asset else None,
            industry=asset.industry if asset else None,
            headquarters=row.headquarters,
            website=row.website,
            is_public=asset is not None,
        )
        store.upsert_company(company)
        if asset is None:
            unresolved.append(row.company_name)
            continue
        security_id = uuid5(NAMESPACE_URL, f"quantmind:security:{ranking_year}:{asset.symbol}:{company_id}")
        store.upsert_security(
            SecurityRecord(
                security_id=security_id,
                company_id=company_id,
                ticker=asset.symbol,
                exchange=row.exchange,
                cik=asset.cik,
            )
        )
        resolved += 1
    return UniverseIngestionReport(
        ranking_year=ranking_year,
        discovered_companies=len(rows),
        resolved_securities=resolved,
        unresolved_companies=unresolved,
        source_url=provider.source_url,
        retrieved_at=retrieved_at,
    )
