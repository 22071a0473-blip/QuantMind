"""Ingest a versioned Fortune 500 CSV and report security resolution."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from quantmind.storage import SQLiteStore
from quantmind.universe import list_universe
from quantmind.universe_ingestion import CsvFortune500Provider, ingest_fortune500


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--source", type=Path, required=True, help="Verified provider-exported CSV.")
    parser.add_argument("--database", type=Path, default=Path("data/quantmind.db"))
    parser.add_argument("--report", type=Path, default=Path("data/fortune500_coverage.json"))
    args = parser.parse_args()
    store = SQLiteStore(args.database)
    try:
        report = ingest_fortune500(
            store=store,
            provider=CsvFortune500Provider(args.source),
            ranking_year=args.year,
            assets=list_universe(),
        )
        args.report.parent.mkdir(parents=True, exist_ok=True)
        payload = asdict(report)
        args.report.write_text(json.dumps(payload, default=str, indent=2), encoding="utf-8")
        print(json.dumps(payload, default=str, indent=2))
    finally:
        store.close()


if __name__ == "__main__":
    main()
