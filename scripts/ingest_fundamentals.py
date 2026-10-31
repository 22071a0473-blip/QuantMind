"""Ingest SEC Company Facts for a resolved security."""

from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path

from quantmind.sec_fundamentals import SecCompanyFactsProvider, persist_company_facts
from quantmind.storage import SQLiteStore


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--cik")
    parser.add_argument("--database", type=Path, default=Path("data/quantmind.db"))
    args = parser.parse_args()
    user_agent = os.environ.get("QUANTMIND_SEC_USER_AGENT", "").strip()
    if not user_agent:
        raise SystemExit("Set QUANTMIND_SEC_USER_AGENT to a real contact identifier.")
    store = SQLiteStore(args.database)
    try:
        security = store.find_security(args.ticker)
        if security is None:
            raise SystemExit("Ticker is not resolved in the canonical store.")
        cik = args.cik or security.cik
        if not cik:
            raise SystemExit("The resolved security has no CIK; pass --cik after verifying the mapping.")
        count = asyncio.run(
            persist_company_facts(
                store=store,
                provider=SecCompanyFactsProvider(user_agent),
                company_id=security.company_id,
                cik=cik,
            )
        )
        print(f"Persisted {count} SEC facts for {args.ticker.upper()}.")
    finally:
        store.close()


if __name__ == "__main__":
    main()
