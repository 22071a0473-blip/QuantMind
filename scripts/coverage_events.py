"""Report source-backed market-event corpus coverage."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from quantmind.event_store import EventStore


def main() -> None:
    store = EventStore(Path("data/quantmind.db"))
    try:
        events = store.list_events(limit=100_000)
    finally:
        store.close()
    by_type = Counter(event.event_type for event in events)
    by_sector = Counter(event.sector or "unknown" for event in events)
    by_year = Counter(str(event.event_date.year) for event in events)
    payload = {
        "total": len(events),
        "by_type": dict(sorted(by_type.items())),
        "by_sector": dict(sorted(by_sector.items())),
        "by_year": dict(sorted(by_year.items())),
        "null_forward_returns": {
            horizon: sum(getattr(event, horizon) is None for event in events)
            for horizon in ("fwd_1d", "fwd_5d", "fwd_20d", "fwd_60d")
        },
        "limited_types": sorted(event_type for event_type, count in by_type.items() if count < 15),
    }
    output = Path("data/event_coverage.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
