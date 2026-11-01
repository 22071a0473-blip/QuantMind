"""Export the structured event corpus in deterministic JSONL order."""

from __future__ import annotations

import argparse
from pathlib import Path

from quantmind.event_store import EventStore


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=Path("data/quantmind.db"))
    parser.add_argument("--output", type=Path, default=Path("data/market_events.jsonl"))
    args = parser.parse_args()
    store = EventStore(args.database)
    try:
        events = store.all_events()
    finally:
        store.close()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        for event in events:
            handle.write(event.model_dump_json(exclude={"created_at"}) + "\n")
    print(f"Exported {len(events)} events to {args.output}.")


if __name__ == "__main__":
    main()
