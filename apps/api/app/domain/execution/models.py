"""
CareerOS Phase 11 — Controlled Application Execution Domain Models.

Strongly typed models for safe execution, idempotency, user handoff,
auditable receipts, and safety gate evaluations.
Core Invariant:
AI proposes. Evidence validates. Rules decide. Humans control exceptions.
"Mark as Submitted" is stored as a User Assertion, never claimed as system proof without verifiable evidence.
"""

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

ExecutionMode = Literal["API", "USER_HANDOFF", "UNSUPPORTED", "UNKNOWN"]

ExecutionStatus = Literal[
    "PREPARED",
    "READY_FOR_REVIEW",
    "APPROVED",
    "EXECUTION_CHECK",
    "BLOCKED",
    "USER_HANDOFF",
    "API_EXECUTION",
    "EXECUTING",
    "SUBMITTED",
    "VERIFIED",
    "FAILED",
    "CANCELLED",
    "EXPIRED",
]

ExecutionEventType = Literal[
    "EXECUTION_STARTED",
    "EXECUTION_BLOCKED",
    "HANDOFF_CREATED",
    "HANDOFF_OPENED",
    "USER_MARKED_SUBMITTED",
    "API_SUBMISSION_STARTED",
    "API_SUBMITTED",
    "SUBMISSION_VERIFIED",
    "EXECUTION_FAILED",
    "EXECUTION_CANCELLED",
]

EvidenceType = Literal[
    "USER_ASSERTION",
    "API_RESPONSE",
    "RECEIPT_HASH",
    "NONE",
]


class SafetyCheckResult(BaseModel):
    """
    Individual safety gate verification result.
    """

    check_name: str
    passed: bool
    reason: str


class SafetyGateEvaluation(BaseModel):
    """
    Evaluation summary of all safety gate checks before execution.
    """

    all_passed: bool
    checks: list[SafetyCheckResult] = Field(default_factory=list)
    blocking_reasons: list[str] = Field(default_factory=list)


class HandoffChecklistItem(BaseModel):
    """
    Actionable checklist item for manual user handoff execution.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    description: str
    action_type: str  # OPEN_URL, COPY_COVER_LETTER, COPY_ANSWER, DOWNLOAD_RESUME, MARK_SUBMITTED
    payload: str | None = None
    completed: bool = False


class HandoffBundle(BaseModel):
    """
    User handoff packet containing all assets needed for manual submission.
    """

    application_url: str
    cover_letter: str | None = None
    answers: list[dict[str, Any]] = Field(default_factory=list)
    resume_download_url: str | None = None
    checklist: list[HandoffChecklistItem] = Field(default_factory=list)
    opened_at: datetime | None = None
    user_confirmed_at: datetime | None = None
    notes: str | None = None


class ExecutionReceipt(BaseModel):
    """
    Auditable cryptographic proof of execution or handoff confirmation.
    """

    execution_id: str
    application_package_id: str
    job_id: str
    execution_mode: ExecutionMode
    status: ExecutionStatus
    idempotency_key: str
    submitted_at: datetime | None = None
    verified_at: datetime | None = None
    evidence_type: EvidenceType = "NONE"
    is_user_assertion: bool = False
    audit_hash: str
    details: dict[str, Any] = Field(default_factory=dict)


class ApplicationExecution(BaseModel):
    """
    Controlled application execution record tracking state, receipts, and handoff.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    application_package_id: str
    user_id: str
    profile_id: str
    job_id: str
    decision_id: str | None = None

    execution_mode: ExecutionMode = "USER_HANDOFF"
    status: ExecutionStatus = "EXECUTION_CHECK"
    idempotency_key: str

    receipt: ExecutionReceipt | None = None
    handoff_details: HandoffBundle | None = None
    safety_gate_results: SafetyGateEvaluation | None = None

    failure_reason: str | None = None
    notes: str | None = None

    submitted_at: datetime | None = None
    verified_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ExecutionAuditEvent(BaseModel):
    """
    Observable audit event emitted during execution lifecycle.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    execution_id: str
    user_id: str
    event_type: ExecutionEventType
    actor: str = "SYSTEM"  # SYSTEM, USER, API_WORKER
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
