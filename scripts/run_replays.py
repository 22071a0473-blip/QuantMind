"""Run chronological, cutoff-safe historical replay forecasts."""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from quantmind.timemachine import TimeMachineService


@dataclass(frozen=True)
class ReplayRunSummary:
    candidates: int
    processed: int
    forecasted: int
    insufficient_analogues: int
    failed: int
    dry_run: bool


async def run_replays(
    service: TimeMachineService,
    *,
    ticker: str | None,
    start: date | None,
    end: date | None,
    horizon_days: int,
    dry_run: bool,
    batch_size: int,
) -> ReplayRunSummary:
    offset = 0
    candidates = []
    while True:
        page = service.candidates(ticker, limit=batch_size, offset=offset)
        if not page.items:
            break
        candidates.extend(page.items)
        offset += len(page.items)
        if offset >= page.total:
            break

    selected = [
        candidate
        for candidate in candidates
        if (start is None or candidate.as_of >= start) and (end is None or candidate.as_of <= end)
    ]
    selected.sort(key=lambda candidate: (candidate.as_of, candidate.ticker, candidate.event_id))
    processed = forecasted = insufficient = failed = 0
    for candidate in selected:
        processed += 1
        try:
            forecast = await service.forecast(
                candidate.ticker,
                candidate.as_of,
                horizon_days,
                persist_hypothesis=not dry_run,
            )
            if forecast.insufficient_analogues:
                insufficient += 1
            else:
                forecasted += 1
        except Exception as exc:
            failed += 1
            print(
                json.dumps(
                    {
                        "event_id": candidate.event_id,
                        "ticker": candidate.ticker,
                        "as_of": candidate.as_of.isoformat(),
                        "error": str(exc),
                    },
                    sort_keys=True,
                )
            )
    return ReplayRunSummary(
        candidates=len(selected),
        processed=processed,
        forecasted=forecasted,
        insufficient_analogues=insufficient,
        failed=failed,
        dry_run=dry_run,
    )


def _date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=Path("data/quantmind.db"))
    parser.add_argument("--ticker")
    parser.add_argument("--start", type=_date)
    parser.add_argument("--end", type=_date)
    parser.add_argument("--horizon-days", type=int, choices=(5, 20, 60), default=20)
    parser.add_argument("--batch-size", type=int, choices=range(1, 501), default=100)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    summary = asyncio.run(
        run_replays(
            TimeMachineService(args.database),
            ticker=args.ticker,
            start=args.start,
            end=args.end,
            horizon_days=args.horizon_days,
            dry_run=args.dry_run,
            batch_size=args.batch_size,
        )
    )
    print(json.dumps(summary.__dict__, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
