"""Backfill source-backed historical market events into Hindsight."""

from __future__ import annotations

import argparse
import asyncio
import json
import math
from collections import Counter
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import yfinance as yf
from quantmind.curated_events import CuratedEvent, load_curated_events
from quantmind.event_memory import QuantMindEventMemory
from quantmind.events import DailyMarketRow, EventRecord, classify_price_event, compute_forward_return
from quantmind.sec_events import FilingEvent, fetch_8k_events


def _universe_asset(ticker: str) -> dict[str, object]:
    payload = json.loads(Path("data/universe.json").read_text(encoding="utf-8-sig"))
    for asset in payload:
        if asset["symbol"] == ticker:
            return asset
    raise ValueError(f"No universe entry found for {ticker}.")


def _universe_cik(ticker: str) -> str:
    asset = _universe_asset(ticker)
    cik = asset.get("cik")
    if not cik:
        raise ValueError(f"No SEC CIK found for {ticker}.")
    return str(cik)


def load_rows(ticker: str, years: int, spy_history: Any) -> list[DailyMarketRow]:
    history = yf.Ticker(ticker).history(
        start=date.today() - timedelta(days=years * 366),
        end=date.today() + timedelta(days=1),
        auto_adjust=False,
    )
    if history.empty:
        return []
    spy_close = spy_history["Close"]
    spy_by_date = {
        spy_close.index[index].date(): float(spy_close.iloc[index] / spy_close.iloc[index - 1] - 1)
        for index in range(1, len(spy_close))
    }
    close = history["Close"].tolist()
    volume = history["Volume"].tolist()
    rows: list[DailyMarketRow] = []
    raw_abnormal = [
        float(close[index] / close[index - 1] - 1) - (spy_by_date.get(history.index[index].date()) or 0.0)
        for index in range(len(history))
    ]
    for index in range(20, len(history)):
        average_volume = sum(volume[max(0, index - 20):index]) / 20
        event_date = history.index[index].date()
        sigma = math.sqrt(sum((value - sum(raw_abnormal[index - 20:index]) / 20) ** 2 for value in raw_abnormal[index - 20:index]) / 20)
        rows.append(DailyMarketRow(
            event_date=event_date,
            close=float(close[index]),
            return_1d=float(close[index] / close[index - 1] - 1),
            return_5d=float(close[index] / close[index - 5] - 1),
            spy_return_1d=spy_by_date.get(event_date),
            abnormal_sigma=sigma or None,
            volume_ratio=float(volume[index] / average_volume) if average_volume else 0,
            high=float(history["High"].iloc[index]),
            low=float(history["Low"].iloc[index]),
        ))
    return rows


def _record_from_row(
    ticker: str,
    row: DailyMarketRow,
    row_index: int,
    closes: list[float],
    event_type: str,
    headline: str | None = None,
    filing_url: str | None = None,
    sector: str | None = None,
    source: str = "Yahoo Finance historical prices",
) -> EventRecord:
    return EventRecord(
        ticker=ticker,
        sector=sector,
        event_date=row.event_date,
        event_type=event_type,  # type: ignore[arg-type]
        headline=headline,
        filing_url=filing_url,
        source=source,
        return_1d=row.return_1d * 100,
        abnormal_return_1d=(row.return_1d - row.spy_return_1d) * 100 if row.spy_return_1d is not None else None,
        volume_ratio=row.volume_ratio,
        close=row.close,
        forward_return_1d=compute_forward_return(closes, row_index, 1),
        forward_return_5d=compute_forward_return(closes, row_index, 5),
        forward_return_20d=compute_forward_return(closes, row_index, 20),
        forward_return_60d=compute_forward_return(closes, row_index, 60),
    )


def event_records(
    ticker: str,
    rows: list[DailyMarketRow],
    filings: list[FilingEvent],
    max_events: int,
    sector: str | None = None,
    curated: list[CuratedEvent] | None = None,
) -> list[EventRecord]:
    closes = [row.close for row in rows]
    row_by_date = {row.event_date: (index, row) for index, row in enumerate(rows)}
    source_records: list[EventRecord] = []
    explained_dates: set[date] = set()
    for event in curated or []:
        match = row_by_date.get(event.event_date)
        if match is None:
            continue
        index, row = match
        source_records.append(
            _record_from_row(
                ticker,
                row,
                index,
                closes,
                event.event_type,
                event.headline,
                str(event.source_url),
                sector,
                "Curated event registry",
            )
        )
        explained_dates.add(event.event_date)
    for filing in filings:
        match = row_by_date.get(filing.event_date)
        if match is None:
            continue
        index, row = match
        if filing.event_type == "earnings":
            explained_dates.add(filing.event_date)
            continue
        source_records.append(
            _record_from_row(
                ticker, row, index, closes, filing.event_type, filing.headline, filing.filing_url, sector
            )
        )
        explained_dates.add(filing.event_date)
    deduplicated_sources: dict[tuple[date, str], EventRecord] = {}
    for record in source_records:
        deduplicated_sources.setdefault((record.event_date, record.event_type), record)

    price_records = []
    for index, row in enumerate(rows):
        if row.event_date in explained_dates:
            continue
        event_type = classify_price_event(row)
        if event_type:
            price_records.append(_record_from_row(ticker, row, index, closes, event_type, sector=sector))
    return list(deduplicated_sources.values()) + price_records[-max_events:]


def earnings_records(
    ticker: str,
    rows: list[DailyMarketRow],
    filings: list[FilingEvent],
    sector: str | None = None,
) -> list[EventRecord]:
    try:
        earnings = yf.Ticker(ticker).get_earnings_dates(limit=100)
    except Exception:
        return []
    closes = [row.close for row in rows]
    row_by_date = {row.event_date: (index, row) for index, row in enumerate(rows)}
    records: list[EventRecord] = []
    candidates: list[tuple[date, float | None, FilingEvent | None]] = []
    filing_earnings = [filing for filing in filings if filing.event_type == "earnings"]
    for timestamp, values in earnings.iterrows():
        event_date = timestamp.date()
        surprise = values.get("Surprise(%)")
        surprise_value = float(surprise) if surprise is not None and str(surprise) != "nan" else None
        filing = min(filing_earnings, key=lambda item: abs((item.event_date - event_date).days), default=None)
        if filing is not None and abs((filing.event_date - event_date).days) > 3:
            filing = None
        candidates.append((event_date, surprise_value, filing))
    records: list[EventRecord] = []
    seen_quarters: set[tuple[int, int]] = set()
    for event_date, surprise, filing in candidates:
        quarter = (event_date.year, (event_date.month - 1) // 3)
        if quarter in seen_quarters:
            continue
        seen_quarters.add(quarter)
        match = row_by_date.get(event_date)
        if match is None:
            continue
        if surprise is None:
            event_type = "earnings"
        else:
            event_type = "earnings_beat" if surprise > 0 else "earnings_miss"
        index, row = match
        records.append(_record_from_row(
            ticker, row, index, closes, event_type,
            filing.headline if filing else f"{ticker} earnings on {event_date.isoformat()}",
            filing.filing_url if filing else None,
            sector,
        ))
    return records


def checkpoint_path(value: str) -> Path:
    return Path(value)


def read_checkpoint(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return set(json.loads(path.read_text(encoding="utf-8")).get("completed_tickers", []))


def write_checkpoint(path: Path, completed: set[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"completed_tickers": sorted(completed)}, indent=2), encoding="utf-8")


def memory_item(record: EventRecord) -> dict[str, Any]:
    return {
        "content": record.to_memory_text(),
        "timestamp": datetime.combine(record.event_date, datetime.min.time(), tzinfo=UTC),
        "document_id": f"event-{record.ticker}-{record.event_date.isoformat()}-{record.event_type}",
        "context": "QuantMind source-backed historical market event.",
        "metadata": {
            "ticker": record.ticker,
            "sector": record.sector or "unknown",
            "event_type": record.event_type,
            "event_date": record.event_date.isoformat(),
            "source": record.source,
            "source_url": record.filing_url,
        },
        "tags": ["historical-event", record.event_type, f"ticker:{record.ticker}", f"sector:{record.sector or 'unknown'}"],
        "update_mode": "replace",
    }


def print_events(records: list[EventRecord]) -> None:
    for record in records:
        print(
            f"{record.event_date.isoformat()} {record.event_type} "
            f"{record.headline or '-'} day0={record.return_1d:.2f}% "
            f"abnormal={record.abnormal_return_1d if record.abnormal_return_1d is not None else 'null'}% "
            f"url={record.filing_url or '-'}"
        )


async def run(args: argparse.Namespace) -> None:
    tickers = [ticker.upper() for ticker in args.tickers]
    completed = read_checkpoint(args.checkpoint)
    spy_history = yf.Ticker("SPY").history(start=date.today() - timedelta(days=args.years * 366), end=date.today() + timedelta(days=1), auto_adjust=False)
    pending_items: list[dict[str, Any]] = []
    pending_tickers: set[str] = set()
    total_counts: Counter[str] = Counter()
    total_record_length = 0
    for ticker in tickers:
        if ticker in completed:
            print(f"{ticker}: skipped (checkpoint)")
            continue
        rows = load_rows(ticker, args.years, spy_history)
        asset = _universe_asset(ticker)
        filings = fetch_8k_events(ticker, _universe_cik(ticker))
        curated = [event for event in load_curated_events() if event.ticker == ticker]
        records = event_records(
            ticker, rows, filings, args.max_events_per_ticker, str(asset.get("sector") or "unknown"), curated
        )
        records.extend(earnings_records(ticker, rows, filings, str(asset.get("sector") or "unknown")))
        counts = Counter(record.event_type for record in records)
        total_counts.update(counts)
        total_record_length += sum(len(record.to_memory_text()) for record in records)
        print(f"{ticker}: {len(rows)} trading rows, {len(records)} events, by type={dict(sorted(counts.items()))}")
        if not args.dry_run:
            pending_items.extend(memory_item(record) for record in records)
            pending_tickers.add(ticker)
    print(f"TOTAL: {sum(total_counts.values())} memories, by type={dict(sorted(total_counts.items()))}")
    average_length = total_record_length / sum(total_counts.values()) if total_counts else 0.0
    print(f"Average record length: {average_length:.0f} characters.")
    print("Hindsight credit cost: unverified; measure from account usage before and after a live run.")
    if not args.dry_run and pending_items:
        operation_id = f"backfill-{','.join(tickers)}-{args.years}-{args.max_events_per_ticker}"
        count = await QuantMindEventMemory().retain_batch(pending_items, operation_id=operation_id)
        completed.update(pending_tickers)
        write_checkpoint(args.checkpoint, completed)
        print(f"Retained {count} memories in quantmind-events.")
    if args.dry_run:
        print("DRY RUN: no Hindsight calls made.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tickers", nargs="*")
    parser.add_argument("--years", type=int, default=5)
    parser.add_argument("--max-events-per-ticker", type=int, default=10)
    parser.add_argument("--list-events", metavar="TICKER")
    parser.add_argument("--type", dest="event_type")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--checkpoint", type=checkpoint_path, default=Path(".cache/quantmind-backfill.json"))
    args = parser.parse_args()
    if args.list_events:
        spy_history = yf.Ticker("SPY").history(start=date.today() - timedelta(days=args.years * 366), end=date.today() + timedelta(days=1), auto_adjust=False)
        ticker = args.list_events.upper()
        rows = load_rows(ticker, args.years, spy_history)
        asset = _universe_asset(ticker)
        filings = fetch_8k_events(ticker, _universe_cik(ticker))
        curated = [event for event in load_curated_events() if event.ticker == ticker]
        records = event_records(
            ticker,
            rows,
            filings,
            args.max_events_per_ticker,
            str(asset.get("sector") or "unknown"),
            curated,
        )
        records.extend(earnings_records(ticker, rows, filings, str(asset.get("sector") or "unknown")))
        print_events([record for record in records if not args.event_type or record.event_type == args.event_type])
    else:
        if not args.tickers:
            parser.error("--tickers is required unless --list-events is used")
        asyncio.run(run(args))


if __name__ == "__main__":
    main()
