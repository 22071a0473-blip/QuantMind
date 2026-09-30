"""Build the cached QuantMind asset universe from public provider catalogs."""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import time
from pathlib import Path
from urllib.request import Request, urlopen

from quantmind.universe import UniverseAsset

NASDAQ_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
OTHER_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"
COINGECKO_URL = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=250&page=1"
SEC_URL = "https://www.sec.gov/files/company_tickers.json"
CACHE_TTL_SECONDS = 86400

# This is the hand-maintained classification layer for the current S&P 100
# membership. Membership is checked against the downloaded Nasdaq catalog; the
# metadata stays stable even when a listing changes its provider display name.
S_AND_P_100 = tuple(dict.fromkeys(
    "AAPL ABBV ABT ACN ADBE AIG AMD AMGN AMT AMZN AVGO AXP BA BAC BK BKNG BMY BRK-B C CAT CHTR CL CMCSA COF COP COST CRM CSCO CVS CVX DE DHR DIS DOW DUK EMR EXC F FDX GD GE GILD GM GOOG GOOGL GS HD HON IBM INTC INTU JNJ JPM KHC KO LIN LLY LMT LOW MA MCD MDLZ MDT MET META MMM MO MRK MS MSFT NEE NFLX NKE NOW NVDA ORCL PEP PFE PG PLTR PM PYPL QCOM RTX SBUX SCHW SO SPG T TGT TMO TMUS TSLA TXN UNH UNP UPS USB V VZ WFC WMT XOM".split()
))

SECTOR_BY_SYMBOL: dict[str, tuple[str, str]] = {
    **dict.fromkeys("AAPL ACN ADBE AMD AVGO CSCO IBM INTC INTU MSFT NVDA ORCL PLTR QCOM TXN".split(), ("Information Technology", "Technology Hardware, Storage & Peripherals")),
    **dict.fromkeys("AMGN ABBV ABT BMY CVS DHR GILD JNJ LLY MDT MRK PFE TMO".split(), ("Health Care", "Pharmaceuticals")),
    **dict.fromkeys("AMZN BKNG CHTR CMCSA DIS NFLX T META GOOG GOOGL".split(), ("Communication Services", "Interactive Media & Services")),
    **dict.fromkeys("AXP BAC BK BKNG C JPM MA MET MS SCHW USB V WFC COF GS".split(), ("Financials", "Banks")),
    **dict.fromkeys("BA CAT DE EMR F FDX GD GE GM HON LMT RTX UNP UPS".split(), ("Industrials", "Aerospace & Defense")),
    **dict.fromkeys("AMT DUK EXC NEE SO".split(), ("Utilities", "Electric Utilities")),
    **dict.fromkeys("CL COST KO KHC LOW MCD MDLZ MO NKE PEP PG PM SBUX TGT WMT".split(), ("Consumer Staples", "Consumer Products")),
    **dict.fromkeys("COP CVX DOW LIN XOM".split(), ("Energy", "Integrated Oil & Gas")),
    **dict.fromkeys("BRK-B".split(), ("Financials", "Multi-Sector Holdings")),
    **dict.fromkeys("AIG".split(), ("Financials", "Insurance")),
    **dict.fromkeys("CRM NOW".split(), ("Information Technology", "Systems Software")),
    **dict.fromkeys("ACN".split(), ("Information Technology", "IT Services")),
    **dict.fromkeys("HON MMM".split(), ("Industrials", "Industrial Conglomerates")),
    **dict.fromkeys("HD SPG".split(), ("Real Estate", "Real Estate Management & Development")),
    **dict.fromkeys("TSLA".split(), ("Consumer Discretionary", "Automobiles")),
    **dict.fromkeys("UNH".split(), ("Health Care", "Managed Health Care")),
    **dict.fromkeys("PYPL".split(), ("Financials", "Consumer Finance")),
    **dict.fromkeys("TMUS VZ".split(), ("Communication Services", "Wireless Telecommunication Services")),
}


def fetch(url: str, user_agent: str) -> bytes:
    request = Request(url, headers={"User-Agent": user_agent})
    with urlopen(request, timeout=30) as response:
        return response.read()


def normalize_symbol(value: str) -> str:
    return value.strip().upper().replace(".", "-")


def clean_name(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", value).strip()
    suffixes = (
        r"\s*-\s*Common Stock$",
        r"\s+Common Stock$",
        r"\s*,?\s*Inc\.?$",
        r"\s*,?\s*Corporation$",
        r"\s*,?\s*Corp\.?$",
        r"\s*,?\s*Holdings?$",
        r"\s*,?\s*Class [A-Z]$",
    )
    previous = ""
    while cleaned != previous:
        previous = cleaned
        for suffix in suffixes:
            cleaned = re.sub(suffix, "", cleaned, flags=re.IGNORECASE).strip()
    return cleaned


def parse_nasdaq(payload: bytes) -> list[UniverseAsset]:
    rows = csv.DictReader(io.StringIO(payload.decode("utf-8-sig")), delimiter="|")
    return [
        UniverseAsset(
            symbol=normalize_symbol(row["Symbol"]),
            name=clean_name(row["Security Name"]),
            kind="etf" if row.get("ETF") == "Y" else "stock",
        )
        for row in rows
        if row.get("Test Issue") == "N"
        and row.get("Symbol")
        and not row["Symbol"].lower().startswith("file creation time")
    ]


def parse_other(payload: bytes) -> list[UniverseAsset]:
    rows = csv.DictReader(io.StringIO(payload.decode("utf-8-sig")), delimiter="|")
    return [
        UniverseAsset(
            symbol=normalize_symbol(row["ACT Symbol"]),
            name=clean_name(row["Security Name"]),
            kind="etf" if row.get("ETF") == "Y" else "stock",
        )
        for row in rows
        if row.get("Test Issue") == "N"
        and row.get("ACT Symbol")
        and not row["ACT Symbol"].lower().startswith("file creation time")
    ]


def parse_sec(payload: bytes) -> dict[str, str]:
    records = json.loads(payload)
    return {
        normalize_symbol(str(item["ticker"])): str(item["cik_str"]).zfill(10)
        for item in records.values()
        if item.get("ticker")
    }


def build(output: Path, cache_dir: Path, user_agent: str) -> int:
    cache_dir.mkdir(parents=True, exist_ok=True)
    now = time.time()

    def cached(name: str, url: str) -> bytes:
        path = cache_dir / name
        if path.exists() and now - path.stat().st_mtime < CACHE_TTL_SECONDS:
            return path.read_bytes()
        payload = fetch(url, user_agent)
        path.write_bytes(payload)
        return payload

    cik_by_ticker = parse_sec(cached("company_tickers.json", SEC_URL))
    assets: dict[str, UniverseAsset] = {}
    for asset in (*parse_nasdaq(cached("nasdaqlisted.txt", NASDAQ_URL)), *parse_other(cached("otherlisted.txt", OTHER_URL))):
        metadata = SECTOR_BY_SYMBOL.get(asset.symbol)
        assets[asset.symbol] = asset.model_copy(update={
            "cik": cik_by_ticker.get(asset.symbol),
            "sector": metadata[0] if metadata else None,
            "industry": metadata[1] if metadata else None,
            "in_sp100": asset.symbol in S_AND_P_100,
            "name": "Berkshire Hathaway Class B" if asset.symbol == "BRK-B" else asset.name,
            "aliases": ["berkshire", "berkshire hathaway"] if asset.symbol == "BRK-B" else asset.aliases,
        })
    for symbol in S_AND_P_100:
        metadata = SECTOR_BY_SYMBOL[symbol]
        assets.setdefault(symbol, UniverseAsset(
            symbol=symbol,
            name=symbol,
            kind="stock",
            sector=metadata[0],
            industry=metadata[1],
            cik=cik_by_ticker.get(symbol),
            in_sp100=True,
        ))
    for item in json.loads(cached("coingecko-top-250.json", COINGECKO_URL)):
        symbol = f"CRYPTO:{item['id']}"
        assets[symbol] = UniverseAsset(
            symbol=symbol,
            name=clean_name(item["name"]),
            kind="crypto",
            sector="Digital Assets",
            industry="Cryptocurrency",
            aliases=[str(item["symbol"]).lower()],
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps([asset.model_dump(exclude={"search_terms"}) for asset in sorted(assets.values(), key=lambda item: item.symbol)], indent=2), encoding="utf-8")
    return len(assets)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("data/universe.json"))
    parser.add_argument("--cache-dir", type=Path, default=Path(".cache/universe"))
    parser.add_argument("--user-agent", default="QuantMind research contact@example.com")
    args = parser.parse_args()
    print(f"Wrote {build(args.output, args.cache_dir, args.user_agent)} assets to {args.output}")
