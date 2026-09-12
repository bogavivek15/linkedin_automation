"""
Unit tests for CareerOS Phase 11 Execution Safety Gates & Policy Engine.
"""

from datetime import datetime, timedelta, timezone

from apps.api.app.domain.application.models import (
    ApplicationAnswer,
    ApplicationPackage,
    ApplicationQuality,
)
from apps.api.app.domain.execution.context import ExecutionContext
from apps.api.app.domain.execution.policy import ExecutionPolicy


def _make_valid_package() -> ApplicationPackage:
    return ApplicationPackage(
        id="pkg-test-1",
        profile_id="prof-1",
        job_id="job-1",
        decision_id="dec-1",
        validation_status="APPROVED",
        quality_status="PASSED",
        quality=ApplicationQuality(
            relevance_score=90.0,
            completeness_score=90.0,
            clarity_score=90.0,
            consistency_score=90.0,
            claim_safety_score=100.0,
            requirement_coverage_score=95.0,
            overall_score=92.0,
        ),
        package_version="v1",
        created_at=datetime.now(timezone.utc),
    )


def test_approved_package_passes_all_gates():
    pkg = _make_valid_package()
    ctx = ExecutionContext(
        user_id="user-1",
        profile_id="prof-1",
        package=pkg,
        job={"status": "ACTIVE", "application_url": "https://company.com/apply"},
        decision={"action": "USER_APPROVAL", "risk_level": "LOW"},
        trust_assessment={"risk_level": "LOW"},
    )
    result = ExecutionPolicy.evaluate(ctx)
    assert result.all_passed is True
    assert len(result.blocking_reasons) == 0


def test_unapproved_package_is_blocked():
    pkg = _make_valid_package()
    pkg.validation_status = "READY_FOR_REVIEW"
    ctx = ExecutionContext(
        user_id="user-1",
        profile_id="prof-1",
        package=pkg,
        job={"status": "ACTIVE"},
        decision={"action": "USER_APPROVAL"},
    )
    result = ExecutionPolicy.evaluate(ctx)
    assert result.all_passed is False
    assert any("must be 'APPROVED'" in r for r in result.blocking_reasons)


def test_expired_package_is_blocked():
    pkg = _make_valid_package()
    pkg.created_at = datetime.now(timezone.utc) - timedelta(days=35)
    ctx = ExecutionContext(
        user_id="user-1",
        profile_id="prof-1",
        package=pkg,
        job={"status": "ACTIVE"},
    )
    result = ExecutionPolicy.evaluate(ctx)
    assert result.all_passed is False
    assert any("expired" in r for r in result.blocking_reasons)


def test_rejected_decision_blocks_execution():
    pkg = _make_valid_package()
    ctx = ExecutionContext(
        user_id="user-1",
        profile_id="prof-1",
        package=pkg,
        job={"status": "ACTIVE"},
        decision={"action": "REJECT", "risk_level": "HIGH"},
    )
    result = ExecutionPolicy.evaluate(ctx)
    assert result.all_passed is False
    assert any("blocks application" in r for r in result.blocking_reasons)


def test_high_risk_trust_blocks_execution():
    pkg = _make_valid_package()
    ctx = ExecutionContext(
        user_id="user-1",
        profile_id="prof-1",
        package=pkg,
        job={"status": "ACTIVE"},
        trust_assessment={"risk_level": "HIGH"},
    )
    result = ExecutionPolicy.evaluate(ctx)
    assert result.all_passed is False
    assert any("HIGH risk" in r for r in result.blocking_reasons)


def test_sensitive_credential_question_blocks_execution():
    pkg = _make_valid_package()
    pkg.application_answers.append(
        ApplicationAnswer(
            question="Please enter your LinkedIn account password for screening",
            answer="secret123",
        )
    )
    ctx = ExecutionContext(
        user_id="user-1",
        profile_id="prof-1",
        package=pkg,
        job={"status": "ACTIVE"},
    )
    result = ExecutionPolicy.evaluate(ctx)
    assert result.all_passed is False
    assert any("prohibited sensitive credentials" in r for r in result.blocking_reasons)


def test_already_submitted_blocks_duplicate():
    pkg = _make_valid_package()
    ctx = ExecutionContext(
        user_id="user-1",
        profile_id="prof-1",
        package=pkg,
        job={"status": "ACTIVE"},
        existing_execution={"status": "SUBMITTED", "submitted_at": datetime.now(timezone.utc).isoformat()},
    )
    result = ExecutionPolicy.evaluate(ctx)
    assert result.all_passed is False
    assert any("already submitted" in r for r in result.blocking_reasons)


def test_default_unsupported_to_user_handoff():
    mode = ExecutionPolicy.resolve_execution_mode("UNKNOWN", {"supports_api_submission": False})
    assert mode == "USER_HANDOFF"

    mode_none = ExecutionPolicy.resolve_execution_mode(None, {})
    assert mode_none == "USER_HANDOFF"
