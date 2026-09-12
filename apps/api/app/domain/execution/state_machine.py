"""
CareerOS Phase 11 — Execution State Machine.

Enforces deterministic, validated transitions across execution lifecycle:
PREPARED -> READY_FOR_REVIEW -> APPROVED -> EXECUTION_CHECK -> (BLOCKED | USER_HANDOFF | API_EXECUTION)
      -> EXECUTING -> SUBMITTED -> VERIFIED
Failure / Exit States: FAILED, CANCELLED, EXPIRED.
"""

from apps.api.app.core.errors import CareerOSError
from apps.api.app.domain.execution.models import ExecutionStatus

LEGAL_TRANSITIONS: dict[ExecutionStatus, set[ExecutionStatus]] = {
    "PREPARED": {"READY_FOR_REVIEW", "CANCELLED", "EXPIRED"},
    "READY_FOR_REVIEW": {"APPROVED", "CANCELLED", "EXPIRED"},
    "APPROVED": {"EXECUTION_CHECK", "CANCELLED", "EXPIRED"},
    "EXECUTION_CHECK": {"BLOCKED", "USER_HANDOFF", "API_EXECUTION", "CANCELLED", "FAILED", "EXPIRED"},
    "BLOCKED": set(),  # Terminal until package is regenerated/reapproved
    "USER_HANDOFF": {"SUBMITTED", "CANCELLED", "EXPIRED"},  # User can mark submitted or cancel
    "API_EXECUTION": {"EXECUTING", "FAILED", "CANCELLED"},
    "EXECUTING": {"SUBMITTED", "FAILED", "CANCELLED"},
    "SUBMITTED": {"VERIFIED"},
    "VERIFIED": set(),  # Terminal success
    "FAILED": set(),    # Terminal failure
    "CANCELLED": set(), # Terminal cancellation
    "EXPIRED": set(),   # Terminal expiration
}


class InvalidExecutionStateTransitionError(CareerOSError):
    """Raised when an illegal state transition is attempted."""

    def __init__(self, from_state: str, to_state: str):
        super().__init__(
            code="INVALID_EXECUTION_STATE_TRANSITION",
            message=f"Cannot transition execution from '{from_state}' to '{to_state}'",
            status_code=400,
        )


def can_transition(from_state: ExecutionStatus, to_state: ExecutionStatus) -> bool:
    """Check whether a state transition is permitted."""
    allowed = LEGAL_TRANSITIONS.get(from_state, set())
    return to_state in allowed


def transition_state(current_state: ExecutionStatus, next_state: ExecutionStatus) -> ExecutionStatus:
    """
    Validate and return the new execution state.
    Raises InvalidExecutionStateTransitionError if illegal.
    """
    if not can_transition(current_state, next_state):
        raise InvalidExecutionStateTransitionError(current_state, next_state)
    return next_state
