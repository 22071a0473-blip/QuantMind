"""Local canonical financial store used by ingestion and evaluation jobs.

SQLite keeps local development portable. The schema uses stable identifiers and
explicit timestamps so the same repository methods can later target PostgreSQL.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Iterable
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .temporal import ensure_utc


class CompanyRecord(BaseModel):
    company_id: UUID = Field(default_factory=uuid4)
    legal_name: str
    fortune_rank_year: int | None = None
    fortune_rank: int | None = None
    sector: str | None = None
    industry: str | None = None
    headquarters: str | None = None
    website: str | None = None
    is_public: bool = False


class SecurityRecord(BaseModel):
    security_id: UUID = Field(default_factory=uuid4)
    company_id: UUID
    ticker: str
    exchange: str | None = None
    currency: str = "USD"
    cik: str | None = None
    valid_from: date | None = None
    valid_to: date | None = None


class MarketBarRecord(BaseModel):
    security_id: UUID
    observed_at: datetime
    open: float
    high: float
    low: float
    close: float
    adjusted_close: float | None = None
    volume: float | None = None
    provider: str
    available_at: datetime
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DataSourceRecord(BaseModel):
    source_id: UUID = Field(default_factory=uuid4)
    provider: str
    source_url: str
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    content_hash: str | None = None


class IngestionJobRecord(BaseModel):
    job_id: UUID = Field(default_factory=uuid4)
    job_type: str
    security_id: UUID | None = None
    status: str = "queued"
    requested_start: date | None = None
    requested_end: date | None = None
    records_received: int = 0
    records_inserted: int = 0
    records_updated: int = 0
    records_rejected: int = 0
    retry_count: int = 0
    last_error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class DataQualityIssueRecord(BaseModel):
    issue_id: UUID = Field(default_factory=uuid4)
    entity_type: str
    entity_id: str
    issue_code: str
    severity: str
    details: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    resolved_at: datetime | None = None


class ResearchReportRecord(BaseModel):
    research_id: UUID
    security_id: UUID | None = None
    information_cutoff: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    content_json: str
    validation_status: str = "validated"


class ForecastRecord(BaseModel):
    forecast_id: UUID = Field(default_factory=uuid4)
    research_id: UUID
    security_id: UUID
    created_at: datetime
    horizon_days: int = Field(gt=0)
    expected_direction: str
    expected_return: float | None = None
    assumptions_json: str = "{}"


class OutcomeRecord(BaseModel):
    forecast_id: UUID
    observed_at: datetime
    realized_return: float
    resolved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    evaluation_status: str = "resolved"


class FinancialFactRecord(BaseModel):
    fact_id: UUID = Field(default_factory=uuid4)
    company_id: UUID
    taxonomy: str
    fact_name: str
    period_start: date | None = None
    period_end: date
    filed_at: datetime
    available_at: datetime
    value: float
    unit: str
    form: str | None = None
    accession: str | None = None
    provider: str
    supersedes_fact_id: UUID | None = None


class CoverageSummary(BaseModel):
    companies: int
    public_companies: int
    securities: int
    market_bars: int
    ingestion_jobs: int
    quality_issues: int
    financial_facts: int = 0


class SecurityCoverage(BaseModel):
    ticker: str
    security_id: UUID
    bars: int
    first_observation: datetime | None
    latest_observation: datetime | None
    quality_issues: int


class SecurityLookup(BaseModel):
    security_id: UUID
    company_id: UUID
    ticker: str
    exchange: str | None = None
    currency: str
    cik: str | None = None


class CoverageExport(BaseModel):
    summary: CoverageSummary
    securities: list[SecurityCoverage] = Field(default_factory=list)


def _iso(value: date | datetime | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return ensure_utc(value).isoformat()
    return value.isoformat()


class SQLiteStore:
    """Idempotent repository for normalized financial records."""

    def __init__(self, path: Path = Path("data/quantmind.db")) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.path)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self.initialize()

    def initialize(self) -> None:
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS companies (
                company_id TEXT PRIMARY KEY,
                legal_name TEXT NOT NULL,
                fortune_rank_year INTEGER,
                fortune_rank INTEGER,
                sector TEXT,
                industry TEXT,
                headquarters TEXT,
                website TEXT,
                is_public INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS securities (
                security_id TEXT PRIMARY KEY,
                company_id TEXT NOT NULL REFERENCES companies(company_id),
                ticker TEXT NOT NULL,
                exchange TEXT,
                currency TEXT NOT NULL,
                cik TEXT,
                valid_from TEXT,
                valid_to TEXT,
                UNIQUE(company_id, ticker)
            );
            CREATE TABLE IF NOT EXISTS market_bars (
                security_id TEXT NOT NULL REFERENCES securities(security_id),
                observed_at TEXT NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                adjusted_close REAL,
                volume REAL,
                provider TEXT NOT NULL,
                available_at TEXT NOT NULL,
                ingested_at TEXT NOT NULL,
                PRIMARY KEY(security_id, observed_at, provider)
            );
            CREATE TABLE IF NOT EXISTS data_sources (
                source_id TEXT PRIMARY KEY,
                provider TEXT NOT NULL,
                source_url TEXT NOT NULL,
                retrieved_at TEXT NOT NULL,
                content_hash TEXT
            );
            CREATE TABLE IF NOT EXISTS ingestion_jobs (
                job_id TEXT PRIMARY KEY,
                job_type TEXT NOT NULL,
                security_id TEXT,
                status TEXT NOT NULL,
                requested_start TEXT,
                requested_end TEXT,
                records_received INTEGER NOT NULL,
                records_inserted INTEGER NOT NULL,
                records_updated INTEGER NOT NULL,
                records_rejected INTEGER NOT NULL,
                retry_count INTEGER NOT NULL,
                last_error TEXT,
                started_at TEXT,
                completed_at TEXT
            );
            CREATE TABLE IF NOT EXISTS quality_issues (
                issue_id TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                issue_code TEXT NOT NULL,
                severity TEXT NOT NULL,
                details TEXT NOT NULL,
                created_at TEXT NOT NULL,
                resolved_at TEXT
            );
            CREATE TABLE IF NOT EXISTS research_reports (
                research_id TEXT PRIMARY KEY,
                security_id TEXT,
                information_cutoff TEXT NOT NULL,
                created_at TEXT NOT NULL,
                content_json TEXT NOT NULL,
                validation_status TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS forecasts (
                forecast_id TEXT PRIMARY KEY,
                research_id TEXT NOT NULL,
                security_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                horizon_days INTEGER NOT NULL,
                expected_direction TEXT NOT NULL,
                expected_return REAL,
                assumptions_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS outcomes (
                forecast_id TEXT PRIMARY KEY,
                observed_at TEXT NOT NULL,
                realized_return REAL NOT NULL,
                resolved_at TEXT NOT NULL,
                evaluation_status TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS financial_facts (
                fact_id TEXT PRIMARY KEY,
                company_id TEXT NOT NULL REFERENCES companies(company_id),
                taxonomy TEXT NOT NULL,
                fact_name TEXT NOT NULL,
                period_start TEXT,
                period_end TEXT NOT NULL,
                filed_at TEXT NOT NULL,
                available_at TEXT NOT NULL,
                value REAL NOT NULL,
                unit TEXT NOT NULL,
                form TEXT,
                accession TEXT,
                provider TEXT NOT NULL,
                supersedes_fact_id TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_market_bars_security_date
                ON market_bars(security_id, observed_at);
            CREATE INDEX IF NOT EXISTS idx_quality_issues_entity
                ON quality_issues(entity_type, entity_id);
            """
        )
        self._connection.execute(
            "INSERT OR IGNORE INTO schema_version(version, applied_at) VALUES (?, ?)",
            (1, _iso(datetime.now(UTC))),
        )
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()

    def upsert_source(self, source: DataSourceRecord) -> None:
        self._connection.execute(
            """
            INSERT OR REPLACE INTO data_sources(
                source_id, provider, source_url, retrieved_at, content_hash
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                str(source.source_id),
                source.provider,
                source.source_url,
                _iso(source.retrieved_at),
                source.content_hash,
            ),
        )
        self._connection.commit()

    def save_ingestion_job(self, job: IngestionJobRecord) -> None:
        self._connection.execute(
            """
            INSERT OR REPLACE INTO ingestion_jobs(
                job_id, job_type, security_id, status, requested_start,
                requested_end, records_received, records_inserted,
                records_updated, records_rejected, retry_count, last_error,
                started_at, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(job.job_id),
                job.job_type,
                str(job.security_id) if job.security_id else None,
                job.status,
                _iso(job.requested_start),
                _iso(job.requested_end),
                job.records_received,
                job.records_inserted,
                job.records_updated,
                job.records_rejected,
                job.retry_count,
                job.last_error,
                _iso(job.started_at),
                _iso(job.completed_at),
            ),
        )
        self._connection.commit()

    def upsert_company(self, company: CompanyRecord) -> None:
        self._connection.execute(
            """
            INSERT INTO companies(
                company_id, legal_name, fortune_rank_year, fortune_rank, sector,
                industry, headquarters, website, is_public
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(company_id) DO UPDATE SET
                legal_name=excluded.legal_name,
                fortune_rank_year=excluded.fortune_rank_year,
                fortune_rank=excluded.fortune_rank,
                sector=excluded.sector,
                industry=excluded.industry,
                headquarters=excluded.headquarters,
                website=excluded.website,
                is_public=excluded.is_public
            """,
            (
                str(company.company_id),
                company.legal_name,
                company.fortune_rank_year,
                company.fortune_rank,
                company.sector,
                company.industry,
                company.headquarters,
                company.website,
                int(company.is_public),
            ),
        )
        self._connection.commit()

    def upsert_security(self, security: SecurityRecord) -> None:
        self._connection.execute(
            """
            INSERT INTO securities(
                security_id, company_id, ticker, exchange, currency, cik,
                valid_from, valid_to
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(security_id) DO UPDATE SET
                company_id=excluded.company_id,
                ticker=excluded.ticker,
                exchange=excluded.exchange,
                currency=excluded.currency,
                cik=excluded.cik,
                valid_from=excluded.valid_from,
                valid_to=excluded.valid_to
            """,
            (
                str(security.security_id),
                str(security.company_id),
                security.ticker,
                security.exchange,
                security.currency,
                security.cik,
                _iso(security.valid_from),
                _iso(security.valid_to),
            ),
        )
        self._connection.commit()

    def upsert_market_bars(self, bars: Iterable[MarketBarRecord]) -> int:
        records = list(bars)
        self._connection.executemany(
            """
            INSERT INTO market_bars(
                security_id, observed_at, open, high, low, close,
                adjusted_close, volume, provider, available_at, ingested_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(security_id, observed_at, provider) DO UPDATE SET
                open=excluded.open,
                high=excluded.high,
                low=excluded.low,
                close=excluded.close,
                adjusted_close=excluded.adjusted_close,
                volume=excluded.volume,
                available_at=excluded.available_at,
                ingested_at=excluded.ingested_at
            """,
            [
                (
                    str(bar.security_id),
                    _iso(bar.observed_at),
                    bar.open,
                    bar.high,
                    bar.low,
                    bar.close,
                    bar.adjusted_close,
                    bar.volume,
                    bar.provider,
                    _iso(bar.available_at),
                    _iso(bar.ingested_at),
                )
                for bar in records
            ],
        )
        self._connection.commit()
        return len(records)

    def count_market_bars(self, security_id: UUID, provider: str, observed_at: Iterable[datetime]) -> int:
        timestamps = [_iso(value) for value in observed_at]
        if not timestamps:
            return 0
        placeholders = ", ".join("?" for _ in timestamps)
        row = self._connection.execute(
            f"""
            SELECT COUNT(*) FROM market_bars
            WHERE security_id = ? AND provider = ? AND observed_at IN ({placeholders})
            """,
            (str(security_id), provider, *timestamps),
        ).fetchone()
        return int(row[0])

    def record_quality_issue(self, issue: DataQualityIssueRecord) -> None:
        self._connection.execute(
            """
            INSERT OR REPLACE INTO quality_issues(
                issue_id, entity_type, entity_id, issue_code, severity,
                details, created_at, resolved_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(issue.issue_id),
                issue.entity_type,
                issue.entity_id,
                issue.issue_code,
                issue.severity,
                issue.details,
                _iso(issue.created_at),
                _iso(issue.resolved_at),
            ),
        )
        self._connection.commit()

    def upsert_financial_fact(self, fact: FinancialFactRecord) -> None:
        self.upsert_financial_facts([fact])

    def upsert_financial_facts(self, facts: Iterable[FinancialFactRecord]) -> int:
        records = list(facts)
        self._connection.executemany(
            """
            INSERT OR REPLACE INTO financial_facts(
                fact_id, company_id, taxonomy, fact_name, period_start,
                period_end, filed_at, available_at, value, unit, form,
                accession, provider, supersedes_fact_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    str(fact.fact_id),
                    str(fact.company_id),
                    fact.taxonomy,
                    fact.fact_name,
                    _iso(fact.period_start),
                    _iso(fact.period_end),
                    _iso(fact.filed_at),
                    _iso(fact.available_at),
                    fact.value,
                    fact.unit,
                    fact.form,
                    fact.accession,
                    fact.provider,
                    str(fact.supersedes_fact_id) if fact.supersedes_fact_id else None,
                )
                for fact in records
            ],
        )
        self._connection.commit()
        return len(records)

    def security_coverage(self, security_id: UUID, ticker: str) -> SecurityCoverage:
        row = self._connection.execute(
            """
            SELECT COUNT(*) AS bars, MIN(observed_at) AS first_observation,
                   MAX(observed_at) AS latest_observation
            FROM market_bars WHERE security_id = ?
            """,
            (str(security_id),),
        ).fetchone()
        issue_count = self._connection.execute(
            "SELECT COUNT(*) FROM quality_issues WHERE entity_type = 'security' AND entity_id = ?",
            (str(security_id),),
        ).fetchone()[0]
        return SecurityCoverage(
            ticker=ticker,
            security_id=security_id,
            bars=int(row["bars"]),
            first_observation=row["first_observation"],
            latest_observation=row["latest_observation"],
            quality_issues=int(issue_count),
        )

    def find_security(self, ticker: str) -> SecurityLookup | None:
        row = self._connection.execute(
            """
            SELECT security_id, company_id, ticker, exchange, currency, cik
            FROM securities WHERE UPPER(ticker) = UPPER(?) ORDER BY security_id LIMIT 1
            """,
            (ticker,),
        ).fetchone()
        if row is None:
            return None
        return SecurityLookup(
            security_id=UUID(row["security_id"]),
            company_id=UUID(row["company_id"]),
            ticker=row["ticker"],
            exchange=row["exchange"],
            currency=row["currency"],
            cik=row["cik"],
        )

    def latest_market_observation(self, security_id: UUID) -> date | None:
        row = self._connection.execute(
            "SELECT MAX(observed_at) AS latest_observation FROM market_bars WHERE security_id = ?",
            (str(security_id),),
        ).fetchone()
        if not row or row["latest_observation"] is None:
            return None
        return date.fromisoformat(str(row["latest_observation"])[:10])

    def coverage_export(self) -> CoverageExport:
        rows = self._connection.execute(
            "SELECT security_id, ticker FROM securities ORDER BY ticker"
        ).fetchall()
        securities = [
            self.security_coverage(UUID(row["security_id"]), row["ticker"])
            for row in rows
        ]
        return CoverageExport(summary=self.coverage(), securities=securities)

    def save_research_report(self, report: ResearchReportRecord) -> None:
        self._connection.execute(
            """
            INSERT OR REPLACE INTO research_reports(
                research_id, security_id, information_cutoff, created_at,
                content_json, validation_status
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(report.research_id),
                str(report.security_id) if report.security_id else None,
                _iso(report.information_cutoff),
                _iso(report.created_at),
                report.content_json,
                report.validation_status,
            ),
        )
        self._connection.commit()

    def save_forecast(self, forecast: ForecastRecord) -> None:
        self._connection.execute(
            """
            INSERT OR REPLACE INTO forecasts(
                forecast_id, research_id, security_id, created_at, horizon_days,
                expected_direction, expected_return, assumptions_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(forecast.forecast_id),
                str(forecast.research_id),
                str(forecast.security_id),
                _iso(forecast.created_at),
                forecast.horizon_days,
                forecast.expected_direction,
                forecast.expected_return,
                forecast.assumptions_json,
            ),
        )
        self._connection.commit()

    def resolve_outcome(self, outcome: OutcomeRecord) -> None:
        self._connection.execute(
            """
            INSERT OR REPLACE INTO outcomes(
                forecast_id, observed_at, realized_return, resolved_at,
                evaluation_status
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                str(outcome.forecast_id),
                _iso(outcome.observed_at),
                outcome.realized_return,
                _iso(outcome.resolved_at),
                outcome.evaluation_status,
            ),
        )
        self._connection.commit()

    def coverage(self) -> CoverageSummary:
        companies = int(self._connection.execute("SELECT COUNT(*) FROM companies").fetchone()[0])
        public_companies = int(
            self._connection.execute("SELECT COUNT(*) FROM companies WHERE is_public = 1").fetchone()[0]
        )
        securities = int(self._connection.execute("SELECT COUNT(*) FROM securities").fetchone()[0])
        market_bars = int(self._connection.execute("SELECT COUNT(*) FROM market_bars").fetchone()[0])
        ingestion_jobs = int(self._connection.execute("SELECT COUNT(*) FROM ingestion_jobs").fetchone()[0])
        quality_issues = int(self._connection.execute("SELECT COUNT(*) FROM quality_issues").fetchone()[0])
        financial_facts = int(self._connection.execute("SELECT COUNT(*) FROM financial_facts").fetchone()[0])
        return CoverageSummary(
            companies=companies,
            public_companies=public_companies,
            securities=securities,
            market_bars=market_bars,
            ingestion_jobs=ingestion_jobs,
            quality_issues=quality_issues,
            financial_facts=financial_facts,
        )

    def export_coverage(self) -> str:
        return json.dumps(self.coverage().model_dump(), indent=2)
