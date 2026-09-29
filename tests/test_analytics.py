from foresight.analytics import InstitutionalAnalytics


def test_analytics_is_regime_aware_and_penalizes_missing_data() -> None:
    result = InstitutionalAnalytics(
        price_move_pct=8.4,
        volume_vs_average=2.7,
        sector_move_pct=2.1,
        memory_count=4,
        evidence_count=5,
    ).calculate()

    assert result.signal_count >= 30
    assert result.available_count < result.signal_count
    assert result.regime == "catalyst_expansion"
    assert result.group_scores["price_and_volume"] > 50
    assert any("coverage=" in item for item in result.audit_trail)


def test_negative_high_volume_move_is_stress_regime() -> None:
    result = InstitutionalAnalytics(price_move_pct=-8, volume_vs_average=3).calculate()

    assert result.regime == "catalyst_stress"
