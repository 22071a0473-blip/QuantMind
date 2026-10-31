from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import yfinance as yf
from pycoingecko import CoinGeckoAPI

from .models import Evidence, MarketSnapshot, NewsItem
from .temporal import ensure_utc

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class LiveResearchData:
    snapshot: MarketSnapshot
    evidence: list[Evidence]
    news: list[NewsItem]
    features: MarketFeatures


@dataclass(slots=True)
class MarketFeatures:
    return_1d: float | None
    return_5d: float | None
    return_20d: float | None
    volatility_20d: float | None
    volume_ratio: float | None
    drawdown_1y: float | None
    momentum_20d: float | None
    trend_slope: float | None
    price_vs_sma20: float | None
    price_vs_sma50: float | None
    high_low_position: float | None
    news_count: float | None


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
        news = self._normalize_news(provider_news)
        features = MarketFeatures(
            return_1d=snapshot.change_pct,
            return_5d=float((close.iloc[-1] / close.iloc[-6] - 1) * 100) if len(close) > 5 else None,
            return_20d=float((close.iloc[-1] / close.iloc[-21] - 1) * 100) if len(close) > 20 else None,
            volatility_20d=float(returns.tail(20).std() * 100),
            volume_ratio=snapshot.volume_ratio,
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
                published_at=item.published_at,
                available_at=item.published_at,
                temporal_uncertainty=item.temporal_uncertainty,
            )
            for item in news
        )
        return LiveResearchData(snapshot=snapshot, evidence=evidence, news=news, features=features)

    @classmethod
    def _normalize_news(cls, items: list[dict[str, Any]]) -> list[NewsItem]:
        normalized: list[NewsItem] = []
        for item in items:
            content = item.get("content")
            payload = content if isinstance(content, dict) else item
            link = payload.get("canonicalUrl") or payload.get("link") or item.get("link")
            if isinstance(link, dict):
                link = link.get("url")
            if not link:
                continue
            timestamp = payload.get("pubDate") or payload.get("providerPublishTime") or item.get("providerPublishTime")
            normalized.append(
                NewsItem(
                    title=str(payload.get("title", "Untitled")),
                    publisher=str(payload.get("provider", payload.get("publisher", "Unknown"))),
                    url=str(link),
                    published=str(timestamp or ""),
                    summary=str(payload.get("summary", "")),
                    published_at=cls._provider_timestamp(timestamp),
                    provider="Yahoo Finance",
                    temporal_uncertainty=not bool(timestamp),
                )
            )
        return normalized

    @staticmethod
    def _provider_timestamp(value: object) -> datetime | None:
        if value is None:
            return None
        try:
            if isinstance(value, str) and "T" in value:
                return ensure_utc(datetime.fromisoformat(value.replace("Z", "+00:00")))
            return ensure_utc(datetime.fromtimestamp(float(value), tz=UTC))
        except (TypeError, ValueError, OSError):
            return None

    def _crypto(self, asset: str) -> LiveResearchData:
        coin_id = asset.lower().replace(" ", "-")
        data = CoinGeckoAPI().get_coin_by_id(coin_id, localization=False, tickers=False, market_data=True)
        market = data["market_data"]
        price = float(market["current_price"]["usd"])
        change = (
            float(market["price_change_percentage_24h"])
            if market.get("price_change_percentage_24h") is not None
            else None
        )
        snapshot = MarketSnapshot(
            asset=f"CRYPTO:{coin_id}",
            kind="crypto",
            price=price,
            change_pct=change or 0.0,
            volume_ratio=None,
            market_cap=float(market["market_cap"]["usd"]),
            history_days=365,
        )
        evidence = [
            Evidence(
                source="CoinGecko",
                url=f"https://www.coingecko.com/en/coins/{coin_id}",
                date=datetime.now(UTC).date().isoformat(),
                snippet=(
                    f"{coin_id} live USD price {price:.4f}; 24-hour change {change:.2f}%."
                    if change is not None
                    else f"{coin_id} live USD price {price:.4f}; 24-hour change unavailable."
                ),
            )
        ]
        features = MarketFeatures(
            return_1d=change,
            return_5d=None,
            return_20d=None,
            volatility_20d=None,
            volume_ratio=None,
            drawdown_1y=None,
            momentum_20d=None,
            trend_slope=None,
            price_vs_sma20=None,
            price_vs_sma50=None,
            high_low_position=None,
            news_count=0,
        )
        return LiveResearchData(snapshot=snapshot, evidence=evidence, news=[], features=features)
