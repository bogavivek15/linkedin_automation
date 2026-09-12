"""
CareerOS Phase 9 — Decision Policy Priority Order Tests.

Ensures that the priority order is strictly enforced:
1. High risk always rejects (no match score can override)
2. Hard constraints always reject
3. UNKNOWN risk requires approval
4. Low trust requires approval
5. Low confidence requires approval
6. User automation policy is respected
7. Application safety constraints are respected
8. Auto-apply is granted only when all gates pass
"""

from uuid import uuid4

from apps.api.app.domain.decision.models import (
    ApplicationContext,
    CandidateAutomationPolicy,
)
from apps.api.app.domain.decision.policy import DecisionPolicyEngine
from apps.api.app.domain.matching.models import (
    MatchAgentOutput,
    MatchConfidence,
)
from apps.api.app.domain.trust.models import (
    ConfidenceLevel,
    RiskLevel,
    TrustAssessment,
)


def _build_match(
    score: float = 95.0,
    hard_constraints_passed: bool = True,
    confidence: MatchConfidence = MatchConfidence.HIGH,
    recommended_resume_id: str | None = "resume-primary",
) -> MatchAgentOutput:
    return MatchAgentOutput(
        profile_id=uuid4(),
        job_id=uuid4(),
        semantic_score=score,
        skill_score=score,
        experience_score=score,
        location_score=score,
        preference_score=score,
        overall_score=score,
        hard_constraints_passed=hard_constraints_passed,
        hard_constraint_failures=[] if hard_constraints_passed else ["Hard constraint failed"],
        confidence=confidence,
        recommended_resume_id=recommended_resume_id,
    )


def _build_trust(
    score: float = 92.0,
    risk_level: RiskLevel = RiskLevel.LOW,
    confidence: ConfidenceLevel = ConfidenceLevel.HIGH,
) -> TrustAssessment:
    return TrustAssessment(
        job_id=uuid4(),
        trust_score=score,
        risk_score=100.0 - score,
        risk_level=risk_level,
        confidence=confidence,
        explanation="Test assessment",
    )


def test_high_risk_overrides_perfect_match():
    """
    Match = 100, Trust = 95, Risk = HIGH
    Safety Invariant: High risk must WIN and produce REJECT.
    """
    engine = DecisionPolicyEngine()
    match = _build_match(score=100.0)
    trust = _build_trust(score=95.0, risk_level=RiskLevel.HIGH)
    policy = CandidateAutomationPolicy(auto_apply_enabled=True, require_user_approval=False)
    context = ApplicationContext(execution_mode="API")

    decision = engine.evaluate(match, trust, policy, context)
    assert decision.action == "REJECT"
    assert decision.overall_score == 99.5
    assert "risk_level=HIGH" in decision.blocking_conditions


def test_hard_constraint_overrides_high_match_and_trust():
    """
    Match = 99, Trust = 95, Risk = LOW, Hard Constraint = FAIL
    Safety Invariant: Hard constraints failure must produce REJECT.
    """
    engine = DecisionPolicyEngine()
    match = _build_match(score=99.0, hard_constraints_passed=False)
    trust = _build_trust(score=95.0, risk_level=RiskLevel.LOW)
    policy = CandidateAutomationPolicy(auto_apply_enabled=True, require_user_approval=False)
    context = ApplicationContext(execution_mode="API")

    decision = engine.evaluate(match, trust, policy, context)
    assert decision.action == "REJECT"
    assert any("hard_constraint_failure" in b for b in decision.blocking_conditions)


def test_unknown_risk_requires_approval():
    """
    Match = 98, Trust = 90, Risk = UNKNOWN
    CareerOS does not have sufficient evidence -> USER_APPROVAL.
    """
    engine = DecisionPolicyEngine()
    match = _build_match(score=98.0)
    trust = _build_trust(score=90.0, risk_level=RiskLevel.UNKNOWN)
    policy = CandidateAutomationPolicy(auto_apply_enabled=True, require_user_approval=False)
    context = ApplicationContext(execution_mode="API")

    decision = engine.evaluate(match, trust, policy, context)
    assert decision.action == "USER_APPROVAL"
    assert "risk_level=UNKNOWN" in decision.blocking_conditions


def test_medium_trust_requires_approval():
    """
    Match = 98, Trust = 79, Risk = MEDIUM
    Trust < 80 must never auto-apply -> USER_APPROVAL.
    """
    engine = DecisionPolicyEngine()
    match = _build_match(score=98.0)
    trust = _build_trust(score=79.0, risk_level=RiskLevel.MEDIUM)
    policy = CandidateAutomationPolicy(auto_apply_enabled=True, require_user_approval=False)
    context = ApplicationContext(execution_mode="API")

    decision = engine.evaluate(match, trust, policy, context)
    assert decision.action == "USER_APPROVAL"
    assert "trust_score_below_80" in decision.blocking_conditions


def test_auto_apply_granted_when_all_conditions_met():
    """
    Match >= 90, Trust >= 80, Risk LOW, Conf HIGH, Constraints pass,
    Auto enabled, no approval required, API mode -> AUTO_APPLY.
    """
    engine = DecisionPolicyEngine()
    match = _build_match(score=95.0)
    trust = _build_trust(score=93.0, risk_level=RiskLevel.LOW)
    policy = CandidateAutomationPolicy(auto_apply_enabled=True, require_user_approval=False)
    context = ApplicationContext(execution_mode="API")

    decision = engine.evaluate(match, trust, policy, context)
    assert decision.action == "AUTO_APPLY"
    assert decision.eligible_for_auto_apply is True
    assert decision.approval_required is False
    assert len(decision.blocking_conditions) == 0
