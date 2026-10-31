"""Backfill or incrementally update one or more securities from market data."""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict
from datetime import date, timedelta
from pathlib import Path
from uuid import UUID

from quantmind.market_ingestion import YFinanceMarketDataProvider, checkpoint_for, ingest_market_history
from quantmind.storage import SQLiteStore


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--security-id", type=UUID)
    parser.add_argument("--start", type=date.fromisoformat)
    parser.add_argument("--end", type=date.fromisoformat, default=date.today())
    parser.add_argument("--years", type=int, default=2)
    parser.add_argument("--incremental", action="store_true")
    parser.add_argument("--database", type=Path, default=Path("data/quantmind.db"))
    parser.add_argument("--checkpoint", type=Path)
    args = parser.parse_args()
    store = SQLiteStore(args.database)
    try:
        security = store.find_security(args.ticker) if args.security_id is None else None
        security_id = args.security_id or (security.security_id if security else None)
        if security_id is None:
            raise SystemExit("Pass --security-id or ingest the ticker through scripts/ingest_universe.py first.")
        if args.incremental:
            latest = store.latest_market_observation(security_id)
            if latest is not None:
                args.start = latest + timedelta(days=1)
        if args.start is None:
            args.start = args.end - timedelta(days=args.years * 366)
        start = args.start
        result = asyncio.run(
            ingest_market_history(
                store=store,
                provider=YFinanceMarketDataProvider(),
                security_id=security_id,
                ticker=args.ticker.upper(),
                start=start,
                end=args.end,
            )
        )
        print(json.dumps(result.job.model_dump(mode="json"), indent=2))
        print(json.dumps(asdict(result.quality), default=str, indent=2))
        print(json.dumps(store.security_coverage(security_id, args.ticker.upper()).model_dump(mode="json"), indent=2))
        if args.checkpoint:
            checkpoint = checkpoint_for(result, args.ticker.upper(), security_id, "yfinance")
            if checkpoint:
                args.checkpoint.parent.mkdir(parents=True, exist_ok=True)
                args.checkpoint.write_text(checkpoint.model_dump_json(indent=2) + "\n", encoding="utf-8")
    finally:
        store.close()


if __name__ == "__main__":
    main()
