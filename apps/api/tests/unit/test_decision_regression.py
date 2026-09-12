"""
CareerOS Phase 9 — Decision Regression Corpus (Scenarios A through O).

Defines 15 deterministic benchmark scenarios covering all expected actions,
blocking conditions, and safety boundaries.
"""

from uuid import uuid4

import pytest
from apps.api.app.domain.decision.models import (
    ApplicationContext,
    CandidateAutomationPolicy,
)
from apps.api.app.domain.decision.policy import DecisionPolicyEngine
from apps.api.app.domain.matching.models import (
    MatchAgentOutput,
    MatchConfidence,
    SkillMatchDetail,
    SkillMatchStatus,
)
from apps.api.app.domain.trust.models import (
    ConfidenceLevel,
    RiskLevel,
    TrustAssessment,
)


def _create_inputs(
    match_score: float = 95.0,
    trust_score: float = 93.0,
    risk_level: RiskLevel = RiskLevel.LOW,
    match_confidence: MatchConfidence = MatchConfidence.HIGH,
    trust_confidence: ConfidenceLevel = ConfidenceLevel.HIGH,
    hard_constraints_passed: bool = True,
    hard_constraint_failures: list[str] | None = None,
    missing_skills: list[str] | None = None,
    recommended_resume_id: str | None = "resume-1",
    auto_apply_enabled: bool = True,
    require_user_approval: bool = False,
    execution_mode: str = "API",
    sensitive_signals: list[str] | None = None,
):
    details = []
    if missing_skills:
        for s in missing_skills:
            details.append(
                SkillMatchDetail(
                    job_skill=s,
                    candidate_skill=None,
                    status=SkillMatchStatus.MISSING,
                    is_required=True,
                )
            )

    match = MatchAgentOutput(
        profile_id=uuid4(),
        job_id=uuid4(),
        semantic_score=match_score,
        skill_score=match_score,
        experience_score=match_score,
        location_score=match_score,
        preference_score=match_score,
        overall_score=match_score,
        hard_constraints_passed=hard_constraints_passed,
        hard_constraint_failures=hard_constraint_failures or ([] if hard_constraints_passed else ["Constraint failed"]),
        confidence=match_confidence,
        missing_skills=missing_skills or [],
        skill_match_details=details,
        recommended_resume_id=recommended_resume_id,
    )

    trust = TrustAssessment(
        job_id=match.job_id,
        trust_score=trust_score,
        risk_score=100.0 - trust_score,
        risk_level=risk_level,
        confidence=trust_confidence,
        explanation="Trust assessment",
    )

    policy = CandidateAutomationPolicy(
        auto_apply_enabled=auto_apply_enabled,
        require_user_approval=require_user_approval,
    )

    context = ApplicationContext(
        execution_mode=execution_mode,  # type: ignore
        sensitive_signals=sensitive_signals or [],
    )

    return match, trust, policy, context


# Scenario definitions: (Name, Match, Trust, Risk, ExpectedScore, ExpectedAction, ExpectedBlockerSubstrings)
SCENARIOS = [
    # A — Perfect candidate + trusted employer
    ("A_perfect_candidate", 95.0, 93.0, RiskLevel.LOW, 94.8, "AUTO_APPLY", []),
    # B — Excellent match + HIGH risk
    ("B_excellent_match_high_risk", 98.0, 31.0, RiskLevel.HIGH, 91.3, "REJECT", ["risk_level=HIGH"]),
    # C — Excellent match + MEDIUM trust (< 80)
    ("C_excellent_match_medium_trust", 96.0, 72.0, RiskLevel.MEDIUM, 93.6, "USER_APPROVAL", ["trust_score_below_80"]),
    # D — Excellent match + UNKNOWN risk
    ("D_excellent_match_unknown_risk", 97.0, 95.0, RiskLevel.UNKNOWN, 96.8, "USER_APPROVAL", ["risk_level=UNKNOWN"]),
    # E — Hard location failure
    ("E_hard_location_failure", 97.0, 95.0, RiskLevel.LOW, 96.8, "REJECT", ["hard_constraint_failure"]),
    # F — Hard employment-type failure
    ("F_hard_employment_failure", 95.0, 92.0, RiskLevel.LOW, 94.7, "REJECT", ["hard_constraint_failure"]),
    # G — Auto-apply disabled
    ("G_auto_apply_disabled", 96.0, 90.0, RiskLevel.LOW, 95.4, "USER_APPROVAL", ["auto_apply_disabled"]),
    # H — Approval required
    ("H_approval_required", 96.0, 95.0, RiskLevel.LOW, 95.9, "USER_APPROVAL", ["user_approval_required"]),
    # I — Low match (< 90 auto apply threshold)
    ("I_low_match", 68.0, 95.0, RiskLevel.LOW, 70.7, "USER_APPROVAL", ["final_score_below_90"]),
    # J — Low confidence
    ("J_low_confidence", 95.0, 92.0, RiskLevel.LOW, 94.7, "USER_APPROVAL", ["confidence_is_LOW"]),
    # K — Missing critical skill
    ("K_missing_critical_skill", 88.0, 92.0, RiskLevel.LOW, 88.4, "IMPROVEMENT_REQUIRED", ["missing_critical_skills"]),
    # L — No suitable resume
    ("L_no_suitable_resume", 92.0, 90.0, RiskLevel.LOW, 91.8, "IMPROVEMENT_REQUIRED", ["no_suitable_resume_available"]),
    # M — OTP required
    ("M_otp_required", 95.0, 92.0, RiskLevel.LOW, 94.7, "USER_APPROVAL", ["sensitive_requirement:OTP"]),
    # N — CAPTCHA required
    ("N_captcha_required", 95.0, 92.0, RiskLevel.LOW, 94.7, "USER_APPROVAL", ["sensitive_requirement:CAPTCHA"]),
    # O — Unsupported application mechanism
    ("O_unsupported_mechanism", 95.0, 92.0, RiskLevel.LOW, 94.7, "USER_APPROVAL", ["execution_mode_not_api:USER_HANDOFF"]),
]


@pytest.mark.parametrize(
    "name,match_s,trust_s,risk_l,expected_score,expected_action,expected_blockers",
    SCENARIOS,
)
def test_regression_scenario(
    name,
    match_s,
    trust_s,
    risk_l,
    expected_score,
    expected_action,
    expected_blockers,
):
    engine = DecisionPolicyEngine()

    hard_passed = not name.startswith(("E_", "F_"))
    auto_enabled = name != "G_auto_apply_disabled"
    approval_req = name == "H_approval_required"
    match_conf = MatchConfidence.LOW if name == "J_low_confidence" else MatchConfidence.HIGH
    missing_skills = ["Distributed Systems"] if name == "K_missing_critical_skill" else []
    resume_id = None if name == "L_no_suitable_resume" else "resume-1"
    exec_mode = "USER_HANDOFF" if name == "O_unsupported_mechanism" else "API"

    sensitive_signals = []
    if name == "M_otp_required":
        sensitive_signals = ["OTP_SUBMISSION"]
    elif name == "N_captcha_required":
        sensitive_signals = ["CAPTCHA_CHALLENGE"]

    match, trust, policy, context = _create_inputs(
        match_score=match_s,
        trust_score=trust_s,
        risk_level=risk_l,
        match_confidence=match_conf,
        hard_constraints_passed=hard_passed,
        missing_skills=missing_skills,
        recommended_resume_id=resume_id,
        auto_apply_enabled=auto_enabled,
        require_user_approval=approval_req,
        execution_mode=exec_mode,
        sensitive_signals=sensitive_signals,
    )

    decision = engine.evaluate(match, trust, policy, context)

    assert decision.overall_score == expected_score
    assert decision.action == expected_action

    for expected_b in expected_blockers:
        assert any(expected_b in b for b in decision.blocking_conditions), (
            f"Scenario {name} missing expected blocker {expected_b}. Found: {decision.blocking_conditions}"
        )
