"""Import a structured event JSONL snapshot into SQLite."""

from __future__ import annotations

import argparse
from pathlib import Path

from quantmind.event_store import EventStore


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=Path("data/quantmind.db"))
    parser.add_argument("--input", type=Path, default=Path("data/market_events.jsonl"))
    args = parser.parse_args()
    store = EventStore(args.database)
    try:
        imported = store.import_jsonl(args.input)
    finally:
        store.close()
    print(f"Imported {imported} events from {args.input}.")


if __name__ == "__main__":
    main()
