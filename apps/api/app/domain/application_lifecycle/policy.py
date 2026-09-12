"""
CareerOS Phase 12 — Lifecycle Transition Policy.

Enforces deterministic, auditable rules on lifecycle status transitions.
Core Invariant:
Never automatically infer SUBMITTED -> INTERVIEW without verified evidence.
Every status transition must have an approved evidence source.
"""

from typing import Any

from apps.api.app.core.errors import CareerOSError
from apps.api.app.domain.application_lifecycle.models import (
    LifecycleEvidenceType,
    LifecycleStatus,
)

ALLOWED_TRANSITIONS: dict[LifecycleStatus, set[LifecycleStatus]] = {
    "DISCOVERED": {"QUALIFIED", "PREPARED", "REJECTED", "ARCHIVED"},
    "QUALIFIED": {"PACKAGE_READY", "AWAITING_APPROVAL", "PREPARED", "REJECTED", "ARCHIVED"},
    "PACKAGE_READY": {"AWAITING_APPROVAL", "APPROVED", "REVIEW_REQUIRED", "ARCHIVED"},
    "AWAITING_APPROVAL": {"APPROVED", "REJECTED", "WITHDRAWN", "ARCHIVED"},
    "PREPARED": {"REVIEW_REQUIRED", "APPROVED", "PACKAGE_READY", "AWAITING_APPROVAL", "ARCHIVED"},
    "REVIEW_REQUIRED": {"APPROVED", "PREPARED", "ARCHIVED"},
    "APPROVED": {"HANDOFF", "SUBMITTED", "WITHDRAWN", "ARCHIVED"},
    "HANDOFF": {"SUBMITTED", "WITHDRAWN", "ARCHIVED"},
    "SUBMITTED": {"ACKNOWLEDGED", "SCREENING", "ASSESSMENT", "NO_RESPONSE", "WITHDRAWN", "REJECTED"},
    "ACKNOWLEDGED": {"SCREENING", "INTERVIEW", "TECHNICAL", "ASSESSMENT", "REJECTED", "WITHDRAWN", "NO_RESPONSE"},
    "SCREENING": {"INTERVIEW", "TECHNICAL", "HR", "ASSESSMENT", "REJECTED", "WITHDRAWN"},
    "ASSESSMENT": {"INTERVIEW", "TECHNICAL", "HR", "OFFER", "REJECTED", "WITHDRAWN"},
    "INTERVIEW": {"INTERVIEW", "TECHNICAL", "HR", "ASSESSMENT", "OFFER", "REJECTED", "WITHDRAWN"},
    "TECHNICAL": {"TECHNICAL", "HR", "INTERVIEW", "OFFER", "REJECTED", "WITHDRAWN"},
    "HR": {"OFFER", "REJECTED", "WITHDRAWN"},
    "OFFER": {"ARCHIVED", "WITHDRAWN"},
    "REJECTED": {"ARCHIVED"},
    "WITHDRAWN": {"ARCHIVED"},
    "NO_RESPONSE": {"ARCHIVED", "REJECTED"},
    "ARCHIVED": set(),
}

# Invariant: Transitions that strictly require non-empty evidence
EVIDENCE_STRICT_TRANSITIONS: set[tuple[LifecycleStatus, LifecycleStatus]] = {
    ("SUBMITTED", "INTERVIEW"),
    ("SCREENING", "INTERVIEW"),
    ("INTERVIEW", "OFFER"),
    ("ASSESSMENT", "OFFER"),
    ("TECHNICAL", "OFFER"),
    ("HR", "OFFER"),
    ("SUBMITTED", "ACKNOWLEDGED"),
}


class InvalidLifecycleTransitionError(CareerOSError):
    """Raised when an illegal or unevidenced transition is requested."""

    def __init__(self, from_status: str, to_status: str, reason: str):
        super().__init__(
            code="INVALID_LIFECYCLE_TRANSITION",
            message=f"Cannot transition application from '{from_status}' to '{to_status}': {reason}",
            status_code=400,
        )


class LifecyclePolicy:
    """
    Validates lifecycle status transitions and enforces evidence requirements.
    """

    @classmethod
    def validate_transition(
        cls,
        from_status: LifecycleStatus,
        to_status: LifecycleStatus,
        evidence_type: LifecycleEvidenceType,
        evidence_details: dict[str, Any] | None = None,
    ) -> None:
        """
        Validate whether a lifecycle transition is legal and adequately evidenced.
        """
        # Invariant: Never automatically infer SUBMITTED -> INTERVIEW without evidence
        if from_status == "SUBMITTED" and to_status == "INTERVIEW":
            raise InvalidLifecycleTransitionError(
                from_status,
                to_status,
                "Direct transition from SUBMITTED to INTERVIEW is prohibited. Transition must progress through ACKNOWLEDGED or SCREENING with recruiter evidence.",
            )

        allowed = ALLOWED_TRANSITIONS.get(from_status, set())
        if to_status not in allowed:
            raise InvalidLifecycleTransitionError(
                from_status,
                to_status,
                f"Transition from '{from_status}' to '{to_status}' is not permitted by lifecycle graph.",
            )

        # Invariant: Advanced progression (e.g. OFFER or INTERVIEW) requires affirmative evidence
        pair = (from_status, to_status)
        if pair in EVIDENCE_STRICT_TRANSITIONS:
            if not evidence_type:
                raise InvalidLifecycleTransitionError(
                    from_status,
                    to_status,
                    "This status change requires an explicit evidence type.",
                )
            if evidence_type not in (
                "RECRUITER_COMMUNICATION",
                "PORTAL_STATUS",
                "IMPORTED_EMAIL",
                "API_RESPONSE",
                "USER_CONFIRMATION",
            ):
                raise InvalidLifecycleTransitionError(
                    from_status,
                    to_status,
                    f"Evidence type '{evidence_type}' is insufficient to prove progression to '{to_status}'.",
                )
