"""SEC submissions provider for source-backed 8-K market events."""

from __future__ import annotations

import gzip
import json
import os
import time
from datetime import UTC, date, datetime
from urllib.request import Request, urlopen

from pydantic import BaseModel

from .taxonomy import FILING_ITEM_TYPES, EventType


class FilingEvent(BaseModel):
    ticker: str
    event_date: date
    event_type: EventType
    item_code: str
    headline: str
    filing_url: str
    available_at: datetime | None = None


def _get_json(url: str, user_agent: str) -> dict[str, object]:
    request = Request(url, headers={"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"})
    with urlopen(request, timeout=30) as response:
        body = response.read()
        if response.headers.get("Content-Encoding") == "gzip":
            body = gzip.decompress(body)
        return json.loads(body)


def fetch_8k_events(ticker: str, cik: str, user_agent: str | None = None) -> list[FilingEvent]:
    agent = user_agent or os.getenv("QUANTMIND_SEC_USER_AGENT") or os.getenv("SEC_USER_AGENT")
    if not agent:
        raise ValueError("QUANTMIND_SEC_USER_AGENT or SEC_USER_AGENT is required for SEC requests.")
    payload = _get_json(f"https://data.sec.gov/submissions/CIK{cik.zfill(10)}.json", agent)
    pages = [payload]
    files = payload.get("filings", {}).get("files", [])  # type: ignore[union-attr]
    for file_entry in files:  # type: ignore[union-attr]
        name = file_entry.get("name")
        if not name:
            continue
        time.sleep(0.2)
        pages.append(_get_json(f"https://data.sec.gov/submissions/{name}", agent))
    time.sleep(0.2)
    events = parse_8k_pages(ticker, cik, pages)
    return sorted(
        {(event.event_date, event.item_code, event.filing_url): event for event in events}.values(),
        key=lambda event: event.event_date,
    )


def parse_8k_submissions(ticker: str, cik: str, payload: dict[str, object]) -> list[FilingEvent]:
    filings = payload.get("filings")
    forms = filings["recent"] if filings else payload
    form_values = forms["form"]  # type: ignore[index]
    dates = forms["filingDate"]  # type: ignore[index]
    accessions = forms["accessionNumber"]  # type: ignore[index]
    primary_documents = forms["primaryDocument"]  # type: ignore[index]
    items = forms["items"]  # type: ignore[index]
    acceptance_times = forms.get("acceptanceDateTime", [""] * len(form_values))  # type: ignore[union-attr]
    results: list[FilingEvent] = []
    for index, form in enumerate(form_values):
        if form != "8-K":
            continue
        matched = [code for code in str(items[index]).split(",") if code in FILING_ITEM_TYPES]
        for code in matched:
            item_description = str(items[index]).replace(",", ", ")
            primary_document = str(primary_documents[index])
            headline = f"8-K {item_description}: {primary_document}"
            event_type = FILING_ITEM_TYPES[code]
            title_lower = headline.lower()
            if code in {"1.01", "2.01"} and any(
                word in title_lower for word in ("merger", "acquisition", "acquire", "business combination")
            ):
                event_type = "merger_acquisition"
            elif code == "1.01" and any(word in title_lower for word in ("partner", "alliance", "collaboration")):
                event_type = "major_partnership_deal"
            accession = str(accessions[index]).replace("-", "")
            accepted = str(acceptance_times[index]) if index < len(acceptance_times) else ""
            available_at = (
                datetime.fromisoformat(accepted.replace("Z", "+00:00")).astimezone(UTC)
                if accepted
                else datetime.combine(date.fromisoformat(str(dates[index])), datetime.min.time(), tzinfo=UTC)
            )
            results.append(
                FilingEvent(
                    ticker=ticker,
                    event_date=date.fromisoformat(str(dates[index])),
                    event_type=event_type,
                    item_code=code,
                    headline=headline,
                    filing_url=f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession}/{primary_document}",
                    available_at=available_at,
                )
            )
    return results


def parse_8k_pages(ticker: str, cik: str, pages: list[dict[str, object]]) -> list[FilingEvent]:
    return [event for page in pages for event in parse_8k_submissions(ticker, cik, page)]
