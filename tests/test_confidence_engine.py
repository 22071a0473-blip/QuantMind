from quantmind.confidence_engine import CONFIDENCE_PARAMETERS, ConfidenceEngine, ConfidenceVector, VECTOR_WEIGHTS


def test_confidence_has_fifty_parameters_and_unit_weights() -> None:
    assert len(CONFIDENCE_PARAMETERS) == 50
    assert sum(VECTOR_WEIGHTS.values()) == 1
    assert {item.vector for item in CONFIDENCE_PARAMETERS} == set(ConfidenceVector)


def test_missing_data_reduces_coverage_without_fake_score() -> None:
    report = ConfidenceEngine().evaluate({"price_change_1d": 120, "rates": -20})
    assert report.score <= 100
    assert report.coverage == 2 / 50
    assert report.available == 2
    assert "volatility" in report.missing

