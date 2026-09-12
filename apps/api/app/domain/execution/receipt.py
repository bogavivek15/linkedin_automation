"""
CareerOS Phase 11 — Execution Receipt Generator.

Generates tamper-evident, auditable execution receipts for submissions and user handoffs.
Core Invariant:
"Mark as Submitted" generates a receipt explicitly flagged as a USER_ASSERTION,
preventing false claims of system-verified external completion.
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from apps.api.app.domain.execution.models import (
    EvidenceType,
    ExecutionMode,
    ExecutionReceipt,
    ExecutionStatus,
)


def generate_execution_receipt(
    execution_id: str,
    package_id: str,
    job_id: str,
    user_id: str,
    execution_mode: ExecutionMode,
    status: ExecutionStatus,
    idempotency_key: str,
    evidence_type: EvidenceType,
    submitted_at: datetime | None = None,
    verified_at: datetime | None = None,
    details: dict[str, Any] | None = None,
) -> ExecutionReceipt:
    """
    Generate an auditable, verifiable ExecutionReceipt with cryptographic hash.
    """
    now = datetime.now(timezone.utc)
    effective_sub_time = submitted_at or (now if status in ("SUBMITTED", "VERIFIED") else None)
    is_assertion = evidence_type == "USER_ASSERTION"
    meta = details or {}

    # Build deterministic canonical string for hashing
    hash_payload = {
        "execution_id": execution_id,
        "package_id": package_id,
        "job_id": job_id,
        "user_id": user_id,
        "mode": execution_mode,
        "status": status,
        "idempotency_key": idempotency_key,
        "evidence_type": evidence_type,
        "is_user_assertion": is_assertion,
        "submitted_at": effective_sub_time.isoformat() if effective_sub_time else None,
    }
    canonical_bytes = json.dumps(hash_payload, sort_keys=True).encode("utf-8")
    audit_hash = hashlib.sha256(canonical_bytes).hexdigest()

    return ExecutionReceipt(
        execution_id=execution_id,
        application_package_id=package_id,
        job_id=job_id,
        execution_mode=execution_mode,
        status=status,
        idempotency_key=idempotency_key,
        submitted_at=effective_sub_time,
        verified_at=verified_at,
        evidence_type=evidence_type,
        is_user_assertion=is_assertion,
        audit_hash=f"sha256:{audit_hash}",
        details=meta,
    )
