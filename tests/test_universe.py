from pathlib import Path

from scripts.build_universe import parse_nasdaq, parse_other, parse_sec
from quantmind.universe import list_universe, search_universe

FIXTURES = Path(__file__).parent / "fixtures"


def test_listing_parsers_normalize_names_symbols_and_etf_flags() -> None:
    nasdaq = parse_nasdaq((FIXTURES / "nasdaqlisted.txt").read_bytes())
    other = parse_other((FIXTURES / "otherlisted.txt").read_bytes())
    assert [(item.symbol, item.name, item.kind) for item in nasdaq] == [
        ("AAPL", "Apple", "stock"),
        ("QQQ", "Invesco QQQ Trust, Series 1", "etf"),
    ]
    assert [(item.symbol, item.name, item.kind) for item in other] == [
        ("BRK-B", "Berkshire Hathaway", "stock"),
        ("SPY", "SPDR S&P 500 ETF Trust", "etf"),
    ]


def test_sec_parser_pads_cik_and_normalizes_class_symbol() -> None:
    payload = b'{"0":{"ticker":"BRK.B","cik_str":1067983}}'
    assert parse_sec(payload) == {"BRK-B": "0001067983"}


def test_search_prioritizes_exact_symbol() -> None:
    result = search_universe("PLTR")
    assert result.results[0].symbol == "PLTR"
    assert result.total >= 1


def test_required_phase_one_queries() -> None:
    expected = {
        "apple": "AAPL",
        "meta plat": "META",
        "berkshire": "BRK-B",
        "nvidia": "NVDA",
        "tesla": "TSLA",
        "BRK-B": "BRK-B",
    }
    for query, symbol in expected.items():
        assert search_universe(query).results[0].symbol == symbol


def test_search_matches_company_alias_and_filters_kind() -> None:
    result = search_universe("palantir")
    assert [asset.symbol for asset in result.results] == ["PLTR"]
    assert all(asset.kind == "stock" for asset in list_universe("stock"))


def test_empty_search_is_explicit() -> None:
    result = search_universe("   ")
    assert result.total == 0
    assert result.results == []


def test_search_limit_bounds_results() -> None:
    result = search_universe("software", limit=1)
    assert len(result.results) == 1
    assert result.total >= len(result.results)
