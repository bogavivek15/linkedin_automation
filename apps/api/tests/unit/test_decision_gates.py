"""
CareerOS Phase 9 — Decision Policy Gate Tests.

Tests each discrete policy gate in isolation.
"""

from uuid import uuid4

from apps.api.app.domain.decision.gates import (
    evaluate_application_safety_gate,
    evaluate_automation_policy_gate,
    evaluate_confidence_gate,
    evaluate_hard_constraint_gate,
    evaluate_high_risk_gate,
    evaluate_improvement_required_gate,
    evaluate_trust_threshold_gate,
    evaluate_unknown_risk_gate,
)
from apps.api.app.domain.decision.models import (
    ApplicationContext,
    CandidateAutomationPolicy,
)
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


def _make_trust(
    trust_score: float = 90.0,
    risk_level: RiskLevel = RiskLevel.LOW,
    confidence: ConfidenceLevel = ConfidenceLevel.HIGH,
) -> TrustAssessment:
    return TrustAssessment(
        job_id=uuid4(),
        trust_score=trust_score,
        risk_score=100.0 - trust_score,
        risk_level=risk_level,
        confidence=confidence,
        explanation="Test assessment",
    )


def _make_match(
    overall_score: float = 95.0,
    hard_constraints_passed: bool = True,
    confidence: MatchConfidence = MatchConfidence.HIGH,
    missing_skills: list[str] | None = None,
    recommended_resume_id: str | None = "resume-1",
) -> MatchAgentOutput:
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

    return MatchAgentOutput(
        profile_id=uuid4(),
        job_id=uuid4(),
        semantic_score=overall_score,
        skill_score=overall_score,
        experience_score=overall_score,
        location_score=overall_score,
        preference_score=overall_score,
        overall_score=overall_score,
        hard_constraints_passed=hard_constraints_passed,
        hard_constraint_failures=[] if hard_constraints_passed else ["Location mismatch"],
        confidence=confidence,
        missing_skills=missing_skills or [],
        skill_match_details=details,
        recommended_resume_id=recommended_resume_id,
    )


def test_high_risk_gate():
    """HIGH risk or trust < 35 triggers gate."""
    # Low risk -> False
    passed, _ = evaluate_high_risk_gate(_make_trust(risk_level=RiskLevel.LOW, trust_score=90.0))
    assert passed is False

    # HIGH risk -> True
    fired, blockers = evaluate_high_risk_gate(_make_trust(risk_level=RiskLevel.HIGH, trust_score=90.0))
    assert fired is True
    assert "risk_level=HIGH" in blockers

    # Trust below 35 -> True
    fired, blockers = evaluate_high_risk_gate(_make_trust(risk_level=RiskLevel.MEDIUM, trust_score=32.0))
    assert fired is True
    assert "trust_score_below_floor_35" in blockers


def test_hard_constraint_gate():
    """Hard constraint failure triggers rejection."""
    passed, _ = evaluate_hard_constraint_gate(_make_match(hard_constraints_passed=True))
    assert passed is False

    fired, blockers = evaluate_hard_constraint_gate(_make_match(hard_constraints_passed=False))
    assert fired is True
    assert any("hard_constraint_failure" in b for b in blockers)


def test_unknown_risk_gate():
    """UNKNOWN risk triggers review gate."""
    passed, _ = evaluate_unknown_risk_gate(_make_trust(risk_level=RiskLevel.LOW))
    assert passed is False

    fired, blockers = evaluate_unknown_risk_gate(_make_trust(risk_level=RiskLevel.UNKNOWN))
    assert fired is True
    assert "risk_level=UNKNOWN" in blockers


def test_trust_threshold_gate():
    """Trust score < 80 requires approval."""
    passed, _ = evaluate_trust_threshold_gate(_make_trust(trust_score=85.0))
    assert passed is False

    fired, blockers = evaluate_trust_threshold_gate(_make_trust(trust_score=79.0))
    assert fired is True
    assert "trust_score_below_80" in blockers


def test_confidence_gate():
    """Confidence LOW in either match or trust triggers gate."""
    m_high = _make_match(confidence=MatchConfidence.HIGH)
    t_high = _make_trust(confidence=ConfidenceLevel.HIGH)
    passed, _ = evaluate_confidence_gate(m_high, t_high)
    assert passed is False

    # Match confidence LOW
    m_low = _make_match(confidence=MatchConfidence.LOW)
    fired, blockers = evaluate_confidence_gate(m_low, t_high)
    assert fired is True
    assert "match_confidence_is_LOW" in blockers

    # Trust confidence LOW
    t_low = _make_trust(confidence=ConfidenceLevel.LOW)
    fired, blockers = evaluate_confidence_gate(m_high, t_low)
    assert fired is True
    assert "trust_confidence_is_LOW" in blockers


def test_automation_policy_gate():
    """Auto-apply disabled or user approval required triggers gate."""
    # Policy with auto apply enabled and no approval
    policy_auto = CandidateAutomationPolicy(auto_apply_enabled=True, require_user_approval=False)
    passed, _ = evaluate_automation_policy_gate(policy_auto)
    assert passed is False

    # Auto apply disabled
    policy_disabled = CandidateAutomationPolicy(auto_apply_enabled=False, require_user_approval=False)
    fired, blockers = evaluate_automation_policy_gate(policy_disabled)
    assert fired is True
    assert "auto_apply_disabled" in blockers

    # Approval required
    policy_approval = CandidateAutomationPolicy(auto_apply_enabled=True, require_user_approval=True)
    fired, blockers = evaluate_automation_policy_gate(policy_approval)
    assert fired is True
    assert "user_approval_required" in blockers


def test_application_safety_gate():
    """Sensitive requirements or non-API mode trigger gate."""
    # Safe API mode
    ctx_safe = ApplicationContext(execution_mode="API")
    passed, _ = evaluate_application_safety_gate(ctx_safe, [])
    assert passed is False

    # Hand-off mode
    ctx_handoff = ApplicationContext(execution_mode="USER_HANDOFF")
    fired, blockers = evaluate_application_safety_gate(ctx_handoff, [])
    assert fired is True
    assert "execution_mode_not_api:USER_HANDOFF" in blockers

    # Sensitive signal present
    fired, blockers = evaluate_application_safety_gate(ctx_safe, ["OTP_SUBMISSION"])
    assert fired is True
    assert "sensitive_requirement:OTP_SUBMISSION" in blockers


def test_improvement_required_gate():
    """Missing critical skills or missing resume trigger improvement gate."""
    m_ok = _make_match(missing_skills=[], recommended_resume_id="resume-1")
    needs_imp, _ = evaluate_improvement_required_gate(m_ok)
    assert needs_imp is False

    # Missing critical skill
    m_missing_skill = _make_match(missing_skills=["Kubernetes"], recommended_resume_id="resume-1")
    fired, blockers = evaluate_improvement_required_gate(m_missing_skill)
    assert fired is True
    assert any("missing_critical_skills" in b for b in blockers)

    # No resume available
    m_no_resume = _make_match(missing_skills=[], recommended_resume_id=None)
    fired, blockers = evaluate_improvement_required_gate(m_no_resume)
    assert fired is True
    assert "no_suitable_resume_available" in blockers
