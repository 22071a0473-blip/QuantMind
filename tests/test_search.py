from quantmind.search import fts_query, parse_query


def test_query_router_uses_structured_strategy_for_market_metric() -> None:
    parsed = parse_query("AAPL 20-day return and volatility")

    assert parsed.intent == "market_metric"
    assert parsed.symbols == ["AAPL"]
    assert parsed.metrics == ["return", "volatility"]
    assert parsed.retrieval_strategy == ["structured"]


def test_query_router_routes_historical_memory_questions() -> None:
    parsed = parse_query("What precedent did we find for PLTR after a contract win?")

    assert parsed.intent == "memory_recall"
    assert parsed.symbols == ["PLTR"]
    assert "hindsight_memory" in parsed.retrieval_strategy


def test_fts_query_quotes_terms_and_ignores_punctuation() -> None:
    assert fts_query("AAPL: contract win?") == '"aapl" AND "contract" AND "win"'
