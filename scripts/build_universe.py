"""Build the cached QuantMind asset universe from public provider catalogs."""

from __future__ import annotations

import argparse
import csv
import io
import json
import time
from pathlib import Path
from urllib.request import Request, urlopen

from quantmind.universe import UniverseAsset

NASDAQ_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
OTHER_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"
COINGECKO_URL = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=250&page=1"
SEC_URL = "https://www.sec.gov/files/company_tickers.json"
S_AND_P_100 = ["AAPL", "ABBV", "ABT", "ACN", "ADBE", "AIG", "AMD", "AMGN", "AMT", "AMZN", "AVGO", "AXP", "BA", "BAC", "BK", "BKNG", "BMY", "BRK-B", "C", "CAT", "CHTR", "CL", "CMCSA", "COF", "COP", "COST", "CRM", "CSCO", "CVS", "CVX", "DE", "DHR", "DIS", "DOW", "DUK", "EMR", "EXC", "F", "FDX", "GD", "GE", "GILD", "GM", "GOOG", "GOOGL", "GS", "HD", "HON", "IBM", "INTC", "INTU", "JNJ", "JPM", "KHC", "KO", "LIN", "LLY", "LMT", "LOW", "MA", "MCD", "MDLZ", "MDT", "MET", "META", "MMM", "MO", "MO", "MRK", "MS", "MSFT", "NEE", "NFLX", "NKE", "NOW", "NVDA", "ORCL", "PEP", "PFE", "PG", "PLTR", "PM", "PYPL", "QCOM", "RTX", "SBUX", "SCHW", "SO", "SPG", "T", "TGT", "TMO", "TMUS", "TSLA", "TXN", "UNH", "UNP", "UPS", "USB", "V", "VZ", "WFC", "WMT", "XOM"]


def fetch(url: str, user_agent: str) -> bytes:
    request = Request(url, headers={"User-Agent": user_agent})
    with urlopen(request, timeout=30) as response:
        return response.read()


def parse_nasdaq(payload: bytes) -> list[UniverseAsset]:
    rows = csv.DictReader(io.StringIO(payload.decode("utf-8")), delimiter="|")
    return [UniverseAsset(symbol=row["Symbol"], name=row["Security Name"], kind="stock") for row in rows if row.get("Test Issue") == "N"]


def parse_other(payload: bytes) -> list[UniverseAsset]:
    rows = csv.DictReader(io.StringIO(payload.decode("utf-8")), delimiter="|")
    return [UniverseAsset(symbol=row["ACT Symbol"], name=row["Security Name"], kind="stock") for row in rows if row.get("Test Issue") == "N"]


def build(output: Path, cache_dir: Path, user_agent: str) -> int:
    cache_dir.mkdir(parents=True, exist_ok=True)
    now = time.time()

    def cached(name: str, url: str) -> bytes:
        path = cache_dir / name
        if path.exists() and now - path.stat().st_mtime < 86400:
            return path.read_bytes()
        payload = fetch(url, user_agent)
        path.write_bytes(payload)
        return payload

    sec = json.loads(fetch(SEC_URL, user_agent))
    cik_by_ticker = {item["ticker"].upper(): str(item["cik_str"]).zfill(10) for item in sec.values()}
    assets = {asset.symbol: asset.model_copy(update={"cik": cik_by_ticker.get(asset.symbol.replace("-", "."))}) for asset in parse_nasdaq(cached("nasdaqlisted.txt", NASDAQ_URL))}
    assets.update({asset.symbol: asset for asset in parse_other(cached("otherlisted.txt", OTHER_URL))})
    for symbol in S_AND_P_100:
        if symbol not in assets:
            assets[symbol] = UniverseAsset(symbol=symbol, name=symbol, kind="stock", cik=cik_by_ticker.get(symbol))
    for item in json.loads(fetch(COINGECKO_URL, user_agent)):
        assets[f"CRYPTO:{item['id']}"] = UniverseAsset(symbol=f"CRYPTO:{item['id']}", name=item["name"], kind="crypto", aliases=[item["symbol"]])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps([asset.model_dump() for asset in sorted(assets.values(), key=lambda asset: asset.symbol)], indent=2), encoding="utf-8")
    return len(assets)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("data/universe.json"))
    parser.add_argument("--cache-dir", type=Path, default=Path(".cache/universe"))
    parser.add_argument("--user-agent", default="QuantMind research contact@example.com")
    args = parser.parse_args()
    print(f"Wrote {build(args.output, args.cache_dir, args.user_agent)} assets to {args.output}")
