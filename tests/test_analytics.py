from quantmind.analytics import InstitutionalAnalytics
from quantmind.sources import MarketFeatures


def test_analytics_uses_real_feature_lattice_and_regime() -> None:
    result = InstitutionalAnalytics(
        features=MarketFeatures(8.4, 10, 15, 2, 2.7, -4, 0.5, 4, 3, 2, 70, 4),
        memory_count=4,
    ).calculate()

    assert result.signals
    assert len(result.signals) == 12
    assert result.regime == "catalyst_expansion"
    assert result.group_scores["price_and_volume"] > 50
    assert any("coverage" not in item for item in result.audit_trail)


def test_negative_high_volume_move_is_stress_regime() -> None:
    result = InstitutionalAnalytics(
        features=MarketFeatures(-8, -10, -15, 2, 3, -30, -0.5, -4, -3, -2, 20, 0),
        memory_count=0,
    ).calculate()

    assert result.regime == "catalyst_stress"
