"""Resolve one forecast against canonical market bars."""

from __future__ import annotations

import argparse
from pathlib import Path

from quantmind.outcomes import persist_resolution, resolve_forecast
from quantmind.storage import ForecastRecord, SQLiteStore


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--forecast", type=Path, required=True, help="JSON ForecastRecord.")
    parser.add_argument("--database", type=Path, default=Path("data/quantmind.db"))
    args = parser.parse_args()
    forecast = ForecastRecord.model_validate_json(args.forecast.read_text(encoding="utf-8"))
    store = SQLiteStore(args.database)
    try:
        security = store.find_security(args.ticker)
        if security is None:
            raise SystemExit(f"No canonical security mapping found for {args.ticker}.")
        bars = store.market_bars_for_security(security.security_id)
        resolution = resolve_forecast(forecast, bars)
        persist_resolution(store, resolution)
        print(resolution.model_dump_json(indent=2))
    finally:
        store.close()


if __name__ == "__main__":
    main()
