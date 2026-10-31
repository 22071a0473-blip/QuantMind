from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from quantmind import app as app_module
from quantmind.storage import ResearchReportRecord, SQLiteStore


class EmptyEventMemory:
    async def search(self, query: str, limit: int) -> list[object]:
        del query, limit
        return []


def test_research_search_executes_local_report_search(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database = tmp_path / "quantmind.db"
    store = SQLiteStore(database)
    try:
        store.save_research_report(
            ResearchReportRecord(
                research_id=uuid4(),
                information_cutoff=datetime(2026, 1, 2, tzinfo=UTC),
                content_json='{"ticker":"AAPL","body":"Apple revenue expanded."}',
            )
        )
    finally:
        store.close()

    monkeypatch.setenv("QUANTMIND_DATABASE", str(database))
    monkeypatch.setattr(app_module, "QuantMindEventMemory", EmptyEventMemory)

    response = TestClient(app_module.app).get("/api/search/research?q=AAPL%20revenue")

    assert response.status_code == 200
    payload = response.json()
    assert payload["lexical_count"] == 1
    assert payload["results"][0]["source_type"] == "research_report"
