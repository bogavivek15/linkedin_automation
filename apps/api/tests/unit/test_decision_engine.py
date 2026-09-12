from apps.api.app.domain.decision.models import DecisionInput
from apps.api.app.services.decision import DecisionEngine



def test_calculate_final_score():
    # 0.90 * 94 + 0.10 * 91 = 84.6 + 9.1 = 93.7
    assert DecisionEngine.calculate_final_score(94.0, 91.0) == 93.7


# Case A: Match = 94, Trust = 91, Risk = LOW, Hard constraint = False -> Expected: AUTO_APPLY
def test_case_a_auto_apply():
    result = DecisionEngine.evaluate(
        DecisionInput(
            match_score=94.0,
            trust_score=91.0,
            risk_level="LOW",
            has_hard_constraint_violation=False,
        )
    )
    assert result.final_score == 93.7
    assert result.outcome == "AUTO_APPLY"
    assert any("Auto-apply criteria satisfied" in r for r in result.reasons)


# Case B: Match = 98, Trust = 31, Risk = HIGH -> Expected: REJECT
def test_case_b_reject_on_high_risk():
    result = DecisionEngine.evaluate(
        DecisionInput(
            match_score=98.0,
            trust_score=31.0,
            risk_level="HIGH",
            has_hard_constraint_violation=False,
        )
    )
    assert result.outcome == "REJECT"
    assert any("Trust check failed" in r for r in result.reasons)


# Case C: Match = 87, Trust = 92, Risk = LOW -> Expected: USER_APPROVAL
def test_case_c_user_approval():
    result = DecisionEngine.evaluate(
        DecisionInput(
            match_score=87.0,
            trust_score=92.0,
            risk_level="LOW",
            has_hard_constraint_violation=False,
        )
    )
    # Final = 0.90 * 87 + 0.10 * 92 = 78.3 + 9.2 = 87.5 (< 90 auto-apply threshold)
    assert result.final_score == 87.5
    assert result.outcome == "USER_APPROVAL"


# Case D: Match = 95, Trust = 90, Risk = LOW, Hard constraint = True -> Expected: REJECT
def test_case_d_reject_on_hard_constraint():
    result = DecisionEngine.evaluate(
        DecisionInput(
            match_score=95.0,
            trust_score=90.0,
            risk_level="LOW",
            has_hard_constraint_violation=True,
        )
    )
    assert result.outcome == "REJECT"
    assert any("Hard constraint failed" in r for r in result.reasons)


# Case E: Match = 95, Trust = 90, Risk = UNKNOWN -> Expected: USER_APPROVAL
def test_case_e_user_approval_on_unknown_risk():
    result = DecisionEngine.evaluate(
        DecisionInput(
            match_score=95.0,
            trust_score=90.0,
            risk_level="UNKNOWN",
            has_hard_constraint_violation=False,
        )
    )
    assert result.outcome == "USER_APPROVAL"
    assert any("UNKNOWN" in r for r in result.reasons)
