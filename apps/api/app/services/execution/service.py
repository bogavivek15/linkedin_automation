"""
CareerOS Phase 11 — Application Execution Service.

Orchestrates safe, idempotent application execution, safety gate evaluation,
routing between API and User Handoff, and observable event emission.
Core Invariant:
AI proposes. Evidence validates. Rules decide. Humans control exceptions.
Repeated execution requests with identical idempotency keys never create duplicates.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from apps.api.app.core.errors import CareerOSError
from apps.api.app.domain.execution.context import ExecutionContext
from apps.api.app.domain.execution.models import (
    ApplicationExecution,
    ExecutionAuditEvent,
    ExecutionMode,
)
from apps.api.app.domain.execution.policy import ExecutionPolicy
from apps.api.app.domain.execution.state_machine import transition_state
from apps.api.app.repositories.application_repository import ApplicationRepository
from apps.api.app.repositories.decision_repository import DecisionRepository
from apps.api.app.repositories.execution_repository import ExecutionRepository
from apps.api.app.repositories.job_repository import JobRepository
from apps.api.app.repositories.trust_repository import TrustRepository
from apps.api.app.services.execution.handoff import UserHandoffCoordinator
from apps.api.app.services.execution.provider import (
    ExecutionProvider,
    MockAPIExecutionProvider,
    UserHandoffProvider,
)


class ExecutionService:
    """
    Service coordinating safe application execution and user handoff workflows.
    """

    def __init__(
        self,
        api_provider: ExecutionProvider | None = None,
        handoff_provider: ExecutionProvider | None = None,
    ):
        self.api_provider = api_provider or MockAPIExecutionProvider()
        self.handoff_provider = handoff_provider or UserHandoffProvider()

    async def execute_application(
        self,
        package_id: UUID | str,
        user_id: UUID,
        idempotency_key: str | None = None,
        requested_mode: str | None = None,
        mode: Any = None,
    ) -> ApplicationExecution:
        """
        Execute or create handoff for an approved application package with idempotency.
        """
        actual_key = idempotency_key or f"exec-{uuid4()}"

        # 1. Idempotency Check: Return existing execution if idempotency key already processed
        existing = await ExecutionRepository.get_by_idempotency_key(actual_key, user_id)
        if existing:
            return existing

        # 2. Load Application Package
        pkg = await ApplicationRepository.get_package(package_id, user_id)
        if not pkg:
            raise CareerOSError(
                code="PACKAGE_NOT_FOUND",
                message=f"Application package '{package_id}' not found for authenticated user",
                status_code=404,
            )

        # 3. Load Context (Job, Decision, Trust Assessment, Existing Executions)
        job = await JobRepository.get_job_by_id(UUID(pkg.job_id), user_id)
        job_dict = job.model_dump(mode="json") if job else {}

        decision = None
        if pkg.decision_id:
            dec_obj = await DecisionRepository.get_decision_by_id(UUID(pkg.decision_id), user_id)
            if dec_obj:
                decision = dec_obj.model_dump(mode="json")

        trust = await TrustRepository.get_by_job_id(UUID(pkg.job_id))
        trust_dict = trust.model_dump(mode="json") if trust else None

        prior_exec = await ExecutionRepository.get_by_package_id(pkg.id, user_id)
        prior_exec_dict = prior_exec.model_dump(mode="json") if prior_exec else None

        context = ExecutionContext(
            user_id=str(user_id),
            profile_id=pkg.profile_id,
            package=pkg,
            job=job_dict,
            decision=decision,
            trust_assessment=trust_dict,
            existing_execution=prior_exec_dict,
            requested_mode=requested_mode,
        )

        # 4. Evaluate 12 Deterministic Safety Gates
        eval_result = ExecutionPolicy.evaluate(context)
        now = datetime.now(timezone.utc)
        exec_id = str(uuid4())

        # 5. Handle Safety Gates Failure -> BLOCKED
        if not eval_result.all_passed:
            blocked_exec = ApplicationExecution(
                id=exec_id,
                application_package_id=str(pkg.id),
                user_id=str(user_id),
                profile_id=pkg.profile_id,
                job_id=pkg.job_id,
                decision_id=pkg.decision_id,
                execution_mode="USER_HANDOFF",
                status="BLOCKED",
                idempotency_key=actual_key,
                safety_gate_results=eval_result,
                failure_reason="; ".join(eval_result.blocking_reasons),
                created_at=now,
                updated_at=now,
            )
            saved = await ExecutionRepository.save_execution(blocked_exec, user_id)
            await ExecutionRepository.save_audit_event(
                ExecutionAuditEvent(
                    execution_id=exec_id,
                    user_id=str(user_id),
                    event_type="EXECUTION_BLOCKED",
                    actor="SYSTEM",
                    payload={"reasons": eval_result.blocking_reasons},
                ),
                user_id,
            )
            return saved

        # 6. Safety Gates Passed -> Determine Execution Mode
        resolved_mode: ExecutionMode = ExecutionPolicy.resolve_execution_mode(
            requested_mode=requested_mode,
            job_metadata=job_dict.get("metadata"),
        )

        initial_execution = ApplicationExecution(
            id=exec_id,
            application_package_id=str(pkg.id),
            user_id=str(user_id),
            profile_id=pkg.profile_id,
            job_id=pkg.job_id,
            decision_id=pkg.decision_id,
            execution_mode=resolved_mode,
            status="EXECUTION_CHECK",
            idempotency_key=actual_key,
            safety_gate_results=eval_result,
            created_at=now,
            updated_at=now,
        )

        # Emit EXECUTION_STARTED event
        await ExecutionRepository.save_audit_event(
            ExecutionAuditEvent(
                execution_id=exec_id,
                user_id=str(user_id),
                event_type="EXECUTION_STARTED",
                actor="SYSTEM",
                payload={"mode": resolved_mode, "package_version": pkg.package_version},
            ),
            user_id,
        )

        # 7. Route based on Execution Mode
        if resolved_mode == "API":
            # API Execution route
            initial_execution.status = "API_EXECUTION"
            await ExecutionRepository.save_audit_event(
                ExecutionAuditEvent(
                    execution_id=exec_id,
                    user_id=str(user_id),
                    event_type="API_SUBMISSION_STARTED",
                    actor="SYSTEM",
                    payload={"provider": "MockAPIExecutionProvider"},
                ),
                user_id,
            )
            # Submit via provider
            receipt, _ = await self.api_provider.prepare_execution(initial_execution, context)
            initial_execution.status = "SUBMITTED"
            initial_execution.submitted_at = receipt.submitted_at or now
            initial_execution.receipt = receipt
            initial_execution.updated_at = now

            await ExecutionRepository.save_audit_event(
                ExecutionAuditEvent(
                    execution_id=exec_id,
                    user_id=str(user_id),
                    event_type="API_SUBMITTED",
                    actor="API_WORKER",
                    payload={"receipt_hash": receipt.audit_hash},
                ),
                user_id,
            )
        else:
            # USER_HANDOFF route (default)
            initial_execution.status = "USER_HANDOFF"
            receipt, bundle = await self.handoff_provider.prepare_execution(initial_execution, context)
            initial_execution.receipt = receipt
            initial_execution.handoff_details = bundle
            initial_execution.updated_at = now

            await ExecutionRepository.save_audit_event(
                ExecutionAuditEvent(
                    execution_id=exec_id,
                    user_id=str(user_id),
                    event_type="HANDOFF_CREATED",
                    actor="SYSTEM",
                    payload={"handoff_url": bundle.application_url if bundle else None},
                ),
                user_id,
            )

        saved = await ExecutionRepository.save_execution(initial_execution, user_id)
        return saved

    async def get_execution(self, execution_id: UUID | str, user_id: UUID) -> ApplicationExecution | None:
        """Retrieve single execution record with isolation."""
        return await ExecutionRepository.get_execution(execution_id, user_id)

    async def get_execution_for_package(self, package_id: UUID | str, user_id: UUID) -> ApplicationExecution | None:
        """Retrieve latest execution for application package."""
        return await ExecutionRepository.get_by_package_id(package_id, user_id)

    async def list_executions(self, user_id: UUID, status: str | None = None) -> list[ApplicationExecution]:
        """List executions for user."""
        return await ExecutionRepository.list_executions(user_id, status)

    async def get_audit_events(self, execution_id: UUID | str, user_id: UUID) -> list[ExecutionAuditEvent]:
        """Get timeline events for an execution."""
        return await ExecutionRepository.get_audit_events(execution_id, user_id)

    async def record_handoff_opened(self, execution_id: UUID | str, user_id: UUID) -> ApplicationExecution:
        """Record user opening external application URL."""
        execution = await ExecutionRepository.get_execution(execution_id, user_id)
        if not execution:
            raise CareerOSError(code="EXECUTION_NOT_FOUND", message="Execution not found", status_code=404)

        updated_exec, event = UserHandoffCoordinator.record_opened(execution)
        await ExecutionRepository.save_execution(updated_exec, user_id)
        await ExecutionRepository.save_audit_event(event, user_id)
        return updated_exec

    async def mark_submitted(
        self,
        execution_id: UUID | str,
        user_id: UUID,
        notes: str | None = None,
    ) -> ApplicationExecution:
        """
        Record candidate assertion that external submission is complete.
        Strict invariant: Marked explicitly as a USER_ASSERTION.
        """
        execution = await ExecutionRepository.get_execution(execution_id, user_id)
        if not execution:
            raise CareerOSError(code="EXECUTION_NOT_FOUND", message="Execution not found", status_code=404)

        updated_exec, event = UserHandoffCoordinator.mark_submitted(execution, notes=notes)
        await ExecutionRepository.save_execution(updated_exec, user_id)
        await ExecutionRepository.save_audit_event(event, user_id)
        return updated_exec

    async def cancel_execution(
        self,
        execution_id: UUID | str,
        user_id: UUID,
        reason: str | None = None,
    ) -> ApplicationExecution:
        """Cancel an ongoing or pending execution."""
        execution = await ExecutionRepository.get_execution(execution_id, user_id)
        if not execution:
            raise CareerOSError(code="EXECUTION_NOT_FOUND", message="Execution not found", status_code=404)

        next_status = transition_state(execution.status, "CANCELLED")
        execution.status = next_status
        execution.failure_reason = reason
        execution.updated_at = datetime.now(timezone.utc)

        await ExecutionRepository.save_execution(execution, user_id)
        await ExecutionRepository.save_audit_event(
            ExecutionAuditEvent(
                execution_id=str(execution.id),
                user_id=str(user_id),
                event_type="EXECUTION_CANCELLED",
                actor="USER",
                payload={"reason": reason},
            ),
            user_id,
        )
        return execution

    async def verify_execution(
        self,
        execution_id: UUID | str,
        user_id: UUID,
        details: dict[str, Any] | None = None,
    ) -> ApplicationExecution:
        """
        Transition SUBMITTED -> VERIFIED when verifiable evidence is received.
        """
        execution = await ExecutionRepository.get_execution(execution_id, user_id)
        if not execution:
            raise CareerOSError(code="EXECUTION_NOT_FOUND", message="Execution not found", status_code=404)

        next_status = transition_state(execution.status, "VERIFIED")
        now = datetime.now(timezone.utc)
        execution.status = next_status
        execution.verified_at = now
        execution.updated_at = now

        if execution.receipt:
            execution.receipt.status = "VERIFIED"
            execution.receipt.verified_at = now
            if details:
                execution.receipt.details.update(details)

        await ExecutionRepository.save_execution(execution, user_id)
        await ExecutionRepository.save_audit_event(
            ExecutionAuditEvent(
                execution_id=str(execution.id),
                user_id=str(user_id),
                event_type="SUBMISSION_VERIFIED",
                actor="SYSTEM",
                payload=details or {},
            ),
            user_id,
        )
        return execution


# Alias for backward compatibility across phases
ApplicationExecutionService = ExecutionService

