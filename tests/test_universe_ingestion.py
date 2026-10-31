from pathlib import Path

from quantmind.storage import SQLiteStore
from quantmind.universe import UniverseAsset
from quantmind.universe_ingestion import CsvFortune500Provider, ingest_fortune500


def test_csv_universe_resolution_reports_unresolved_rows(tmp_path: Path) -> None:
    source = tmp_path / "fortune.csv"
    source.write_text(
        "rank,company,ticker,exchange\n1,Apple,AAPL,NASDAQ\n2,Private Example,,\n",
        encoding="utf-8",
    )
    store = SQLiteStore(tmp_path / "quantmind.db")
    try:
        report = ingest_fortune500(
            store,
            CsvFortune500Provider(source),
            2025,
            [UniverseAsset(symbol="AAPL", name="Apple", kind="stock", cik="0000320193")],
        )
        assert report.discovered_companies == 2
        assert report.resolved_securities == 1
        assert report.unresolved_companies == ["Private Example"]
        assert store.coverage().companies == 2
        assert store.coverage().securities == 1
        ingest_fortune500(
            store,
            CsvFortune500Provider(source),
            2025,
            [UniverseAsset(symbol="AAPL", name="Apple", kind="stock", cik="0000320193")],
        )
        assert store.coverage().companies == 2
        assert store.coverage().securities == 1
    finally:
        store.close()
