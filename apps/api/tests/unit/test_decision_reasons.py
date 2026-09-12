"""
CareerOS Phase 9 — Decision Reasons Tests.

Validates that structured reasons and blocking conditions are derived
strictly from factual evidence without fabrication.
"""

from apps.api.app.domain.decision.models import (
    ApplicationContext,
    CandidateAutomationPolicy,
)
from apps.api.app.domain.decision.reasons import generate_decision_reasons


def test_reasons_for_auto_apply():
    """Validates reason content for AUTO_APPLY outcome."""
    reasons = generate_decision_reasons(
        action="AUTO_APPLY",
        match_score=95.0,
        trust_score=93.0,
        final_score=94.8,
        risk_level="LOW",
        confidence="HIGH",
        hard_constraints_passed=True,
        policy=CandidateAutomationPolicy(auto_apply_enabled=True, require_user_approval=False),
        application_context=ApplicationContext(execution_mode="API"),
        blocking_conditions=[],
    )

    assert any("Final score 94.8 >= 90.0" in r for r in reasons)
    assert any("All explicit candidate hard constraints passed" in r for r in reasons)
    assert any("candidate automation policy explicitly permits" in r.lower() for r in reasons)
    assert any("mechanism is verified: API" in r for r in reasons)


def test_reasons_for_rejection_high_risk():
    """Validates reason content for high-risk REJECT."""
    reasons = generate_decision_reasons(
        action="REJECT",
        match_score=98.0,
        trust_score=31.0,
        final_score=91.3,
        risk_level="HIGH",
        confidence="MEDIUM",
        hard_constraints_passed=True,
        policy=CandidateAutomationPolicy(auto_apply_enabled=True),
        application_context=ApplicationContext(execution_mode="API"),
        blocking_conditions=["risk_level=HIGH"],
    )

    assert any("Risk level is HIGH" in r for r in reasons)
    assert any("Trust score is 31.0" in r for r in reasons)


def test_reasons_for_rejection_hard_constraints():
    """Validates reason content for hard constraint failure."""
    reasons = generate_decision_reasons(
        action="REJECT",
        match_score=96.0,
        trust_score=90.0,
        final_score=95.4,
        risk_level="LOW",
        confidence="HIGH",
        hard_constraints_passed=False,
        policy=CandidateAutomationPolicy(auto_apply_enabled=True),
        application_context=ApplicationContext(execution_mode="API"),
        blocking_conditions=["hard_constraint_failure:Location mismatch"],
    )

    assert any("violates explicit candidate hard constraints" in r for r in reasons)


def test_reasons_for_improvement_required():
    """Validates reason content for profile improvement."""
    reasons = generate_decision_reasons(
        action="IMPROVEMENT_REQUIRED",
        match_score=75.0,
        trust_score=92.0,
        final_score=76.7,
        risk_level="LOW",
        confidence="MEDIUM",
        hard_constraints_passed=True,
        policy=CandidateAutomationPolicy(auto_apply_enabled=True),
        application_context=ApplicationContext(execution_mode="API"),
        blocking_conditions=["missing_critical_skills:Kubernetes"],
        improvement_reasons=["missing_critical_skills:Kubernetes"],
    )

    assert any("requires enhancement" in r for r in reasons)
    assert any("missing_critical_skills:Kubernetes" in r for r in reasons)
