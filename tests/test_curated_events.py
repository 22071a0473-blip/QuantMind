from datetime import date
from pathlib import Path

from quantmind.curated_events import load_curated_events


def test_known_events_are_source_backed_and_typed() -> None:
    events = load_curated_events(Path("data/known_events.csv"))
    assert len(events) >= 5
    assert all(event.ticker == event.ticker.upper() for event in events)
    assert all(event.event_date >= date(2020, 1, 1) for event in events)
    assert all(str(event.source_url).startswith(("http://", "https://")) for event in events)
