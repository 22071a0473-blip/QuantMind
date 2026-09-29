from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import yfinance as yf
from pycoingecko import CoinGeckoAPI

from .models import Evidence, MarketSnapshot, NewsItem


@dataclass(slots=True)
class LiveResearchData:
    snapshot: MarketSnapshot
    evidence: list[Evidence]
    news: list[NewsItem]


class LiveMarketSources:
    """Acquire live stock or crypto context; no fixture data is used."""

    async def gather(self, asset: str) -> LiveResearchData:
        normalized = asset.strip().upper()
        if normalized.startswith("CRYPTO:"):
            return await asyncio.to_thread(self._crypto, normalized.removeprefix("CRYPTO:"))
        return await asyncio.to_thread(self._stock, normalized)

    def _stock(self, ticker_symbol: str) -> LiveResearchData:
        ticker = yf.Ticker(ticker_symbol)
        history = ticker.history(period="1y", auto_adjust=False)
        if history.empty or "Close" not in history or "Volume" not in history:
            raise ValueError(f"No live market history was returned for {ticker_symbol}.")
        close = history["Close"].dropna()
        volume = history["Volume"].dropna()
        latest_price = float(close.iloc[-1])
        previous_price = float(close.iloc[-2]) if len(close) > 1 else latest_price
        average_volume = float(volume.tail(30).mean())
        latest_volume = float(volume.iloc[-1])
        info: dict[str, Any] = ticker.fast_info
        market_cap = info.get("market_cap")
        snapshot = MarketSnapshot(
            asset=ticker_symbol,
            kind="stock",
            price=latest_price,
            change_pct=((latest_price / previous_price) - 1) * 100,
            volume_ratio=latest_volume / average_volume if average_volume else None,
            market_cap=float(market_cap) if market_cap else None,
            history_days=len(close),
        )
        news = [
            NewsItem(
                title=str(item.get("title", "Untitled")),
                publisher=str(item.get("publisher", "Unknown")),
                url=str(item.get("link", "")),
                published=str(item.get("providerPublishTime", "")),
                summary=str(item.get("summary", "")),
            )
            for item in ticker.news[:12]
            if item.get("link")
        ]
        evidence = [
            Evidence(
                source="Yahoo Finance price history",
                url=f"https://finance.yahoo.com/quote/{ticker_symbol}",
                date=datetime.now(UTC).date().isoformat(),
                snippet=(
                    f"{ticker_symbol} last price {latest_price:.4f}; one-day move "
                    f"{snapshot.change_pct:.2f}%; volume ratio {snapshot.volume_ratio or 0:.2f}x."
                ),
            )
        ]
        evidence.extend(
            Evidence(
                source=item.publisher,
                url=item.url,
                date=item.published,
                snippet=item.summary or item.title,
            )
            for item in news
        )
        return LiveResearchData(snapshot=snapshot, evidence=evidence, news=news)

    def _crypto(self, asset: str) -> LiveResearchData:
        coin_id = asset.lower().replace(" ", "-")
        data = CoinGeckoAPI().get_coin_by_id(coin_id, localization=False, tickers=False, market_data=True)
        market = data["market_data"]
        price = float(market["current_price"]["usd"])
        change = float(market.get("price_change_percentage_24h", 0))
        snapshot = MarketSnapshot(
            asset=f"CRYPTO:{coin_id}",
            kind="crypto",
            price=price,
            change_pct=change,
            volume_ratio=None,
            market_cap=float(market["market_cap"]["usd"]),
            history_days=365,
        )
        evidence = [
            Evidence(
                source="CoinGecko",
                url=f"https://www.coingecko.com/en/coins/{coin_id}",
                date=datetime.now(UTC).date().isoformat(),
                snippet=f"{coin_id} live USD price {price:.4f}; 24-hour change {change:.2f}%.",
            )
        ]
        return LiveResearchData(snapshot=snapshot, evidence=evidence, news=[])
