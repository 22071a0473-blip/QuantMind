"""Resolve elapsed hypotheses from the local canonical market store."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from quantmind.ledger_store import LedgerStore
from quantmind.resolver import resolve_open


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--ticker")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--database", default=os.getenv("QUANTMIND_DATABASE", "data/quantmind.db"))
    args = parser.parse_args()
    store = LedgerStore(Path(args.database))
    try:
        rows = store.list_hypotheses(ticker=args.ticker, limit=args.limit)
        if args.dry_run:
            for row in rows:
                print(f"{row['id']} {row['ticker']} {row['status']} resolves_after={row['resolve_after']}")
            print(f"dry_run candidates={len(rows)}")
            return 0
        resolved = resolve_open(store, ticker=args.ticker, limit=args.limit)
        print(f"resolved={len(resolved)}")
        counts = {row["status"]: int(row["count"]) for row in store.stats()}
        for status in ("open", "censored", "resolved", "invalidated"):
            print(f"{status}={counts.get(status, 0)}")
        if resolved:
            resolved_metrics = [store.get_resolution(item.hypothesis_id) for item in resolved]
            brier_values = [float(row["brier"]) for row in resolved_metrics if row is not None]
            if brier_values:
                print(f"mean_brier={sum(brier_values) / len(brier_values):.6f}")
        return 0
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
