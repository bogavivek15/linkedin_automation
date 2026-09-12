"""
CareerOS Phase 11 — Execution Domain.
"""

from apps.api.app.domain.execution.context import ExecutionContext
from apps.api.app.domain.execution.models import (
    ApplicationExecution,
    EvidenceType,
    ExecutionAuditEvent,
    ExecutionEventType,
    ExecutionMode,
    ExecutionReceipt,
    ExecutionStatus,
    HandoffBundle,
    HandoffChecklistItem,
    SafetyCheckResult,
    SafetyGateEvaluation,
)
from apps.api.app.domain.execution.policy import ExecutionPolicy
from apps.api.app.domain.execution.receipt import generate_execution_receipt
from apps.api.app.domain.execution.state_machine import (
    InvalidExecutionStateTransitionError,
    can_transition,
    transition_state,
)

__all__ = [
    "ApplicationExecution",
    "EvidenceType",
    "ExecutionAuditEvent",
    "ExecutionContext",
    "ExecutionEventType",
    "ExecutionMode",
    "ExecutionPolicy",
    "ExecutionReceipt",
    "ExecutionStatus",
    "HandoffBundle",
    "HandoffChecklistItem",
    "InvalidExecutionStateTransitionError",
    "SafetyCheckResult",
    "SafetyGateEvaluation",
    "can_transition",
    "generate_execution_receipt",
    "transition_state",
]
