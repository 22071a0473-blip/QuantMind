"""Replay retained memory records and report observable precedent counts."""

from __future__ import annotations

import argparse
import asyncio

from quantmind.config import Settings
from quantmind.logging_config import configure_logging
from quantmind.memory import HindsightMemory


async def main(asset: str, query: str) -> None:
    settings = Settings.from_env()
    configure_logging(settings)
    if not settings.hindsight_token:
        raise SystemExit("HINDSIGHT_API_TOKEN is required; set it in the environment.")
    result = await HindsightMemory().recall(asset, query)
    print(f"{result.bank_id}: {len(result.records)} recalled, {result.total_count} total")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("asset")
    parser.add_argument("--query", default="historical market precedent")
    args = parser.parse_args()
    asyncio.run(main(args.asset, args.query))

