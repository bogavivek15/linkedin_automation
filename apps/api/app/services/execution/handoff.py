"""
CareerOS Phase 11 — User Handoff Coordinator.

Coordinates manual application handoff workflows, tracks checklist progress,
records external portal open timestamps, and processes user submission assertions.
Core Invariant:
"Mark as Submitted" is strictly marked as a USER_ASSERTION.
"""

from datetime import datetime, timezone

from apps.api.app.domain.execution.models import (
    ApplicationExecution,
    ExecutionAuditEvent,
    ExecutionReceipt,
)
from apps.api.app.domain.execution.receipt import generate_execution_receipt
from apps.api.app.domain.execution.state_machine import transition_state


class UserHandoffCoordinator:
    """
    Coordinates user handoff operations and state updates.
    """

    @classmethod
    def record_opened(cls, execution: ApplicationExecution) -> tuple[ApplicationExecution, ExecutionAuditEvent]:
        """
        Record that the candidate has opened the external application link.
        """
        now = datetime.now(timezone.utc)
        if execution.handoff_details:
            execution.handoff_details.opened_at = now
            # Mark the "Open Application Portal" item as completed
            for item in execution.handoff_details.checklist:
                if item.action_type == "OPEN_URL":
                    item.completed = True

        execution.updated_at = now

        event = ExecutionAuditEvent(
            execution_id=execution.id,
            user_id=execution.user_id,
            event_type="HANDOFF_OPENED",
            actor="USER",
            payload={
                "url": execution.handoff_details.application_url if execution.handoff_details else None,
                "opened_at": now.isoformat(),
            },
        )
        return execution, event

    @classmethod
    def mark_submitted(
        cls,
        execution: ApplicationExecution,
        notes: str | None = None,
    ) -> tuple[ApplicationExecution, ExecutionAuditEvent]:
        """
        User asserts that the external application has been submitted.
        Produces an auditable USER_ASSERTION receipt.
        """
        now = datetime.now(timezone.utc)

        # Transition state using state machine
        next_status = transition_state(execution.status, "SUBMITTED")
        execution.status = next_status
        execution.submitted_at = now
        execution.notes = notes

        if execution.handoff_details:
            execution.handoff_details.user_confirmed_at = now
            execution.handoff_details.notes = notes
            for item in execution.handoff_details.checklist:
                if item.action_type == "MARK_SUBMITTED":
                    item.completed = True

        # Generate User Assertion Receipt
        receipt: ExecutionReceipt = generate_execution_receipt(
            execution_id=execution.id,
            package_id=execution.application_package_id,
            job_id=execution.job_id,
            user_id=execution.user_id,
            execution_mode=execution.execution_mode,
            status="SUBMITTED",
            idempotency_key=execution.idempotency_key,
            evidence_type="USER_ASSERTION",
            submitted_at=now,
            details={
                "notes": notes,
                "user_confirmed_at": now.isoformat(),
                "assertion_notice": "Confirmed by candidate on external portal.",
            },
        )
        execution.receipt = receipt
        execution.updated_at = now

        event = ExecutionAuditEvent(
            execution_id=execution.id,
            user_id=execution.user_id,
            event_type="USER_MARKED_SUBMITTED",
            actor="USER",
            payload={
                "submitted_at": now.isoformat(),
                "is_user_assertion": True,
                "notes": notes,
                "receipt_hash": receipt.audit_hash,
            },
        )
        return execution, event
