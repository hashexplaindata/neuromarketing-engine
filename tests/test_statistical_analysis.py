import pytest

from scripts.statistical_analysis import analyze_ab, analyze_factorial


def test_analyze_ab_reports_observed_effect_and_holm_adjustment():
    observations = [
        {"unit": "c1", "variant": "control", "click": 0.20},
        {"unit": "c2", "variant": "control", "click": 0.25},
        {"unit": "c3", "variant": "control", "click": 0.30},
        {"unit": "t1", "variant": "treatment", "click": 0.35},
        {"unit": "t2", "variant": "treatment", "click": 0.40},
        {"unit": "t3", "variant": "treatment", "click": 0.45},
    ]
    result = analyze_ab(
        observations,
        outcome="click",
        variant="variant",
        control="control",
        randomized=True,
        unit_key="unit",
        bootstrap_samples=100,
    )
    comparison = result["comparisons"]["treatment"]
    assert result["analysis_mode"] == "EMPIRICAL_OBSERVED_OUTCOMES"
    assert comparison["absolute_difference"] > 0
    assert len(comparison["confidence_interval_95"]) == 2
    assert "p_value_holm" in comparison


def test_analyze_factorial_reports_main_and_interaction_terms():
    observations = []
    for a in ("0", "1"):
        for b in ("0", "1"):
            for replicate in range(3):
                observations.append({
                    "unit": f"{a}{b}-{replicate}",
                    "a": a,
                    "b": b,
                    "score": 10 + 3 * int(a) + 2 * int(b) + int(a) * int(b) + replicate * 0.1,
                })
    result = analyze_factorial(
        observations,
        outcome="score",
        factors=["a", "b"],
        randomized=True,
        unit_key="unit",
    )
    assert result["analysis_type"] == "FULL_FACTORIAL_ANOVA"
    assert set(result["terms"]) == {"a", "b", "a:b"}
    assert result["terms"]["a"]["estimate"] > 0
    assert "p_value_holm" in result["terms"]["a:b"]


def test_factorial_requires_replicated_cells():
    with pytest.raises(ValueError, match="Every factorial cell"):
        analyze_factorial(
            [{"a": "0", "b": "0", "score": 1}, {"a": "0", "b": "1", "score": 2}, {"a": "1", "b": "0", "score": 3}, {"a": "1", "b": "1", "score": 4}],
            outcome="score",
            factors=["a", "b"],
        )
