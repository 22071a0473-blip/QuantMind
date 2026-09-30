from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import yfinance as yf
from pycoingecko import CoinGeckoAPI

from .models import Evidence, MarketSnapshot, NewsItem

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class LiveResearchData:
    snapshot: MarketSnapshot
    evidence: list[Evidence]
    news: list[NewsItem]
    features: MarketFeatures


@dataclass(slots=True)
class MarketFeatures:
    return_1d: float
    return_5d: float
    return_20d: float
    volatility_20d: float
    volume_ratio: float
    drawdown_1y: float
    momentum_20d: float
    trend_slope: float
    price_vs_sma20: float
    price_vs_sma50: float
    high_low_position: float
    news_count: float


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
        returns = close.pct_change().dropna()
        sma20 = float(close.tail(20).mean())
        sma50 = float(close.tail(50).mean())
        year_high = float(close.max())
        year_low = float(close.min())
        try:
            provider_news = ticker.news[:12]
        except Exception as exc:
            # Yahoo's news endpoint is independently rate-limited; preserve
            # usable price history when only the news request fails.
            logger.warning("Yahoo news unavailable for %s: %s", ticker_symbol, exc)
            provider_news = []
        news = [
            NewsItem(
                title=str(item.get("title", "Untitled")),
                publisher=str(item.get("publisher", "Unknown")),
                url=str(item.get("link", "")),
                published=str(item.get("providerPublishTime", "")),
                summary=str(item.get("summary", "")),
            )
            for item in provider_news
            if item.get("link")
        ]
        features = MarketFeatures(
            return_1d=snapshot.change_pct,
            return_5d=float((close.iloc[-1] / close.iloc[-6] - 1) * 100) if len(close) > 5 else snapshot.change_pct,
            return_20d=float((close.iloc[-1] / close.iloc[-21] - 1) * 100) if len(close) > 20 else snapshot.change_pct,
            volatility_20d=float(returns.tail(20).std() * 100),
            volume_ratio=snapshot.volume_ratio or 1,
            drawdown_1y=float((latest_price / year_high - 1) * 100),
            momentum_20d=float(returns.tail(20).mean() * 100),
            trend_slope=float((close.tail(20).iloc[-1] - close.tail(20).iloc[0]) / max(sma20, 0.0001) * 100),
            price_vs_sma20=float((latest_price / sma20 - 1) * 100),
            price_vs_sma50=float((latest_price / sma50 - 1) * 100),
            high_low_position=float((latest_price - year_low) / max(year_high - year_low, 0.0001) * 100),
            news_count=float(len(news)),
        )
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
        return LiveResearchData(snapshot=snapshot, evidence=evidence, news=news, features=features)

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
        features = MarketFeatures(
            return_1d=change,
            return_5d=change,
            return_20d=change,
            volatility_20d=0,
            volume_ratio=1,
            drawdown_1y=float(market.get("ath_change_percentage", {}).get("usd", 0)),
            momentum_20d=change,
            trend_slope=change,
            price_vs_sma20=change,
            price_vs_sma50=change,
            high_low_position=50,
            news_count=0,
        )
        return LiveResearchData(snapshot=snapshot, evidence=evidence, news=[], features=features)
