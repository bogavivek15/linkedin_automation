"""
CareerOS Phase 9 — Decision Scoring Tests.

Tests the deterministic trust-weighted composite score:
    Final = 0.90 * M + 0.10 * T
Boundary checks, clamping, and hand-calculated test cases.
"""

from apps.api.app.domain.decision.scoring import calculate_final_score


def test_scoring_boundaries():
    """Validates 0 and 100 boundaries."""
    assert calculate_final_score(0.0, 0.0) == 0.0
    assert calculate_final_score(100.0, 100.0) == 100.0


def test_scoring_clamping():
    """Values below 0 or above 100 must be clamped before and after weighting."""
    # Negative match clamped to 0: 0.9*0 + 0.1*50 = 5.0
    assert calculate_final_score(-15.0, 50.0) == 5.0
    # Negative trust clamped to 0: 0.9*90 + 0.1*0 = 81.0
    assert calculate_final_score(90.0, -20.0) == 81.0
    # Values above 100 clamped: 0.9*100 + 0.1*100 = 100.0
    assert calculate_final_score(150.0, 120.0) == 100.0


def test_scoring_hand_calculated_intermediate_values():
    """Verify exact formula matches for known scenario cases."""
    # 94 & 91: 84.6 + 9.1 = 93.7
    assert calculate_final_score(94.0, 91.0) == 93.7
    # 95 & 93: 85.5 + 9.3 = 94.8
    assert calculate_final_score(95.0, 93.0) == 94.8
    # 98 & 31: 88.2 + 3.1 = 91.3
    assert calculate_final_score(98.0, 31.0) == 91.3
    # 89 & 93: 80.1 + 9.3 = 89.4
    assert calculate_final_score(89.0, 93.0) == 89.4
    # 96 & 72: 86.4 + 7.2 = 93.6
    assert calculate_final_score(96.0, 72.0) == 93.6
    # 68 & 95: 61.2 + 9.5 = 70.7
    assert calculate_final_score(68.0, 95.0) == 70.7


def test_scoring_weights_sum_to_one():
    """Verify that when M=T=X, Final=X."""
    for score in [0.0, 25.5, 50.0, 75.25, 90.0, 100.0]:
        assert calculate_final_score(score, score) == round(score, 2)
