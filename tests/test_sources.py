from quantmind.sources import LiveMarketSources


def test_normalize_news_accepts_legacy_yfinance_payload() -> None:
    items = LiveMarketSources._normalize_news(
        [
            {
                "title": "Legacy headline",
                "publisher": "Example Wire",
                "link": "https://example.test/legacy",
                "providerPublishTime": 1_700_000_000,
                "summary": "Legacy summary",
            }
        ]
    )

    assert len(items) == 1
    assert items[0].title == "Legacy headline"
    assert items[0].url == "https://example.test/legacy"
    assert items[0].published_at is not None


def test_normalize_news_accepts_nested_yfinance_payload() -> None:
    items = LiveMarketSources._normalize_news(
        [
            {
                "content": {
                    "title": "Nested headline",
                    "provider": "Example Wire",
                    "canonicalUrl": {"url": "https://example.test/nested"},
                    "pubDate": "2024-01-02T03:04:05Z",
                    "summary": "Nested summary",
                }
            }
        ]
    )

    assert len(items) == 1
    assert items[0].title == "Nested headline"
    assert items[0].url == "https://example.test/nested"
    assert items[0].published_at is not None
