"""
Unit tests for CareerOS Phase 11 Execution Receipt Generator.
"""

from datetime import datetime, timezone

from apps.api.app.domain.execution.receipt import generate_execution_receipt


def test_user_assertion_receipt_clearly_flagged():
    receipt = generate_execution_receipt(
        execution_id="exec-123",
        package_id="pkg-456",
        job_id="job-789",
        user_id="user-001",
        execution_mode="USER_HANDOFF",
        status="SUBMITTED",
        idempotency_key="idemp-abc",
        evidence_type="USER_ASSERTION",
        submitted_at=datetime.now(timezone.utc),
    )

    assert receipt.is_user_assertion is True
    assert receipt.evidence_type == "USER_ASSERTION"
    assert receipt.audit_hash.startswith("sha256:")
    assert len(receipt.audit_hash) == 71  # "sha256:" + 64 hex chars


def test_api_receipt_flagged_as_verified_evidence():
    receipt = generate_execution_receipt(
        execution_id="exec-999",
        package_id="pkg-456",
        job_id="job-789",
        user_id="user-001",
        execution_mode="API",
        status="SUBMITTED",
        idempotency_key="idemp-def",
        evidence_type="API_RESPONSE",
        submitted_at=datetime.now(timezone.utc),
    )

    assert receipt.is_user_assertion is False
    assert receipt.evidence_type == "API_RESPONSE"
    assert receipt.audit_hash.startswith("sha256:")


def test_deterministic_hash_generation():
    dt = datetime(2026, 9, 10, 12, 0, 0, tzinfo=timezone.utc)
    r1 = generate_execution_receipt(
        execution_id="e1",
        package_id="p1",
        job_id="j1",
        user_id="u1",
        execution_mode="USER_HANDOFF",
        status="SUBMITTED",
        idempotency_key="k1",
        evidence_type="USER_ASSERTION",
        submitted_at=dt,
    )
    r2 = generate_execution_receipt(
        execution_id="e1",
        package_id="p1",
        job_id="j1",
        user_id="u1",
        execution_mode="USER_HANDOFF",
        status="SUBMITTED",
        idempotency_key="k1",
        evidence_type="USER_ASSERTION",
        submitted_at=dt,
    )
    assert r1.audit_hash == r2.audit_hash
