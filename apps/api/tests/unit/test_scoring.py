"""
CareerOS Phase 8 — Scoring Formula Tests.

Validates: M = 0.30S + 0.30K + 0.15E + 0.10L + 0.15P
"""

from apps.api.app.domain.matching.scoring import calculate_overall_score


def test_all_zeros():
    """S=K=E=L=P=0 → M=0"""
    assert calculate_overall_score(0, 0, 0, 0, 0) == 0.0


def test_all_hundreds():
    """S=K=E=L=P=100 → M=100"""
    assert calculate_overall_score(100, 100, 100, 100, 100) == 100.0


def test_known_intermediate_values():
    """Hand-calculated intermediate values."""
    # M = 0.30×80 + 0.30×90 + 0.15×70 + 0.10×100 + 0.15×60
    # M = 24 + 27 + 10.5 + 10 + 9 = 80.5
    result = calculate_overall_score(80, 90, 70, 100, 60)
    assert result == 80.5


def test_semantic_only():
    """Only semantic score present."""
    # M = 0.30×100 + 0 + 0 + 0 + 0 = 30.0
    result = calculate_overall_score(100, 0, 0, 0, 0)
    assert result == 30.0


def test_skill_only():
    """Only skill score present."""
    # M = 0 + 0.30×100 + 0 + 0 + 0 = 30.0
    result = calculate_overall_score(0, 100, 0, 0, 0)
    assert result == 30.0


def test_experience_only():
    """Only experience score present."""
    # M = 0 + 0 + 0.15×100 + 0 + 0 = 15.0
    result = calculate_overall_score(0, 0, 100, 0, 0)
    assert result == 15.0


def test_location_only():
    """Only location score present."""
    # M = 0 + 0 + 0 + 0.10×100 + 0 = 10.0
    result = calculate_overall_score(0, 0, 0, 100, 0)
    assert result == 10.0


def test_preference_only():
    """Only preference score present."""
    # M = 0 + 0 + 0 + 0 + 0.15×100 = 15.0
    result = calculate_overall_score(0, 0, 0, 0, 100)
    assert result == 15.0


def test_clamping_above_100():
    """Values above 100 should be clamped."""
    result = calculate_overall_score(200, 200, 200, 200, 200)
    assert result == 100.0


def test_clamping_below_0():
    """Negative values should be clamped to 0."""
    result = calculate_overall_score(-10, -10, -10, -10, -10)
    assert result == 0.0


def test_weights_sum_to_one():
    """The weights 0.30 + 0.30 + 0.15 + 0.10 + 0.15 = 1.00"""
    from apps.api.app.domain.matching.scoring import (
        W_EXPERIENCE,
        W_LOCATION,
        W_PREFERENCE,
        W_SEMANTIC,
        W_SKILL,
    )

    total = W_SEMANTIC + W_SKILL + W_EXPERIENCE + W_LOCATION + W_PREFERENCE
    assert abs(total - 1.0) < 1e-10


def test_decimal_precision():
    """Check that rounding handles typical decimal values."""
    # M = 0.30×94 + 0.30×96 + 0.15×100 + 0.10×100 + 0.15×90
    # M = 28.2 + 28.8 + 15 + 10 + 13.5 = 95.5
    result = calculate_overall_score(94, 96, 100, 100, 90)
    assert result == 95.5


def test_another_intermediate():
    """Another hand-calculated example."""
    # M = 0.30×50 + 0.30×75 + 0.15×60 + 0.10×80 + 0.15×40
    # M = 15 + 22.5 + 9 + 8 + 6 = 60.5
    result = calculate_overall_score(50, 75, 60, 80, 40)
    assert result == 60.5
