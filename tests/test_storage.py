from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from quantmind.storage import (
    CompanyRecord,
    DataQualityIssueRecord,
    MarketBarRecord,
    SecurityRecord,
    SQLiteStore,
)


def test_storage_upserts_entities_and_market_bars(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "quantmind.db")
    try:
        company = CompanyRecord(legal_name="Example Holdings", is_public=True)
        security = SecurityRecord(company_id=company.company_id, ticker="EXM")
        store.upsert_company(company)
        store.upsert_security(security)
        bar = MarketBarRecord(
            security_id=security.security_id,
            observed_at=datetime(2026, 1, 2, tzinfo=UTC),
            open=10,
            high=11,
            low=9,
            close=10.5,
            provider="test",
            available_at=datetime(2026, 1, 2, 22, tzinfo=UTC),
        )
        assert store.upsert_market_bars([bar, bar]) == 2
        assert store.coverage().model_dump() == {
            "companies": 1,
            "public_companies": 1,
            "securities": 1,
            "market_bars": 1,
            "ingestion_jobs": 0,
            "quality_issues": 0,
        }
    finally:
        store.close()


def test_storage_preserves_quality_issues(tmp_path: Path) -> None:
    store = SQLiteStore(tmp_path / "quantmind.db")
    try:
        issue = DataQualityIssueRecord(
            entity_type="market_bar",
            entity_id=str(uuid4()),
            issue_code="missing_interval",
            severity="warning",
            details="A trading session is missing.",
        )
        store.record_quality_issue(issue)
        assert store.coverage().quality_issues == 1
    finally:
        store.close()
