from quantmind.universe import list_universe, search_universe


def test_search_prioritizes_exact_symbol() -> None:
    result = search_universe("PLTR")
    assert result.results[0].symbol == "PLTR"
    assert result.total >= 1


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
