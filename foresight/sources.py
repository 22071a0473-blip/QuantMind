"""Live, free-first evidence sources with explicit failure states."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import aiohttp

from .models import Evidence


@dataclass(slots=True)
class SourceBundle:
    evidence: list[Evidence]
    source_status: dict[str, str]
    price: float | None = None
    market_cap: float | None = None


@dataclass(slots=True)
class PriceResult:
    price: float | None
    market_cap: float | None
    status: str


class MarketSources:
    """Fetch market context without allowing an unavailable source to invent data."""

    def __init__(self) -> None:
        self._user_agent = os.getenv("FORESIGHT_SEC_USER_AGENT", "Foresight research contact@example.com")

    async def gather(self, asset: str) -> SourceBundle:
        evidence: list[Evidence] = []
        statuses: dict[str, str] = {}
        price: float | None = None
        market_cap: float | None = None
        timeout = aiohttp.ClientTimeout(total=12)
        headers = {"User-Agent": self._user_agent, "Accept": "application/json"}
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            price_result = await self._price(session, asset)
            price, market_cap = price_result.price, price_result.market_cap
            statuses["market_price"] = price_result.status
            filings, status = await self._sec_filings(session, asset)
            evidence.extend(filings)
            statuses["sec_filings"] = status
        return SourceBundle(evidence=evidence, source_status=statuses, price=price, market_cap=market_cap)

    async def _price(
        self, session: aiohttp.ClientSession, asset: str
    ) -> PriceResult:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{asset.upper()}?range=1mo&interval=1d"
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    return PriceResult(None, None, f"unavailable:{response.status}")
                payload: dict[str, Any] = await response.json()
            result = payload["chart"]["result"][0]
            meta = result["meta"]
            return PriceResult(meta.get("regularMarketPrice"), meta.get("marketCap"), "ok")
        except (aiohttp.ClientError, KeyError, IndexError, TypeError, ValueError) as exc:
            return PriceResult(None, None, f"unavailable:{type(exc).__name__}")

    async def _sec_filings(
        self, session: aiohttp.ClientSession, asset: str
    ) -> tuple[list[Evidence], str]:
        ticker_url = "https://www.sec.gov/files/company_tickers.json"
        try:
            async with session.get(ticker_url) as response:
                if response.status != 200:
                    return [], f"unavailable:{response.status}"
                tickers: dict[str, dict[str, Any]] = await response.json()
            match = next(
                (entry for entry in tickers.values() if entry.get("ticker", "").upper() == asset.upper()),
                None,
            )
            if match is None:
                return [], "not_found"
            cik = str(match["cik_str"]).zfill(10)
            submissions_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
            async with session.get(submissions_url) as response:
                if response.status != 200:
                    return [], f"unavailable:{response.status}"
                payload: dict[str, Any] = await response.json()
            recent = payload["filings"]["recent"]
            output: list[Evidence] = []
            for index, form in enumerate(recent["form"]):
                if form not in {"8-K", "10-Q", "10-K", "DEF 14A", "4"} or len(output) >= 8:
                    continue
                accession = recent["accessionNumber"][index].replace("-", "")
                primary = recent["primaryDocument"][index]
                filing_date = recent["filingDate"][index]
                output.append(
                    Evidence(
                        source=f"SEC {form}",
                        url=f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession}/{primary}",
                        date=filing_date or datetime.now(UTC).date().isoformat(),
                        snippet=f"Recent {form} filing for {asset.upper()}; retrieve the filing before making a claim.",
                    )
                )
            return output, "ok"
        except (aiohttp.ClientError, KeyError, IndexError, TypeError, ValueError) as exc:
            return [], f"unavailable:{type(exc).__name__}"


def evidence_as_prompt(evidence: list[Evidence]) -> str:
    """Create a bounded evidence packet for an optional synthesis model."""
    return "\n".join(
        f"[{item.date}] {item.source}: {item.snippet} ({item.url})" for item in evidence[:24]
    )
