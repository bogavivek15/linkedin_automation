"""
CareerOS Phase 11 — Execution Providers.

Provides provider abstractions for API-based submission and User Handoff.
₹0-compatible: MockAPIExecutionProvider enables complete offline testing without external side effects.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from uuid import uuid4

from apps.api.app.domain.execution.context import ExecutionContext
from apps.api.app.domain.execution.models import (
    ApplicationExecution,
    ExecutionReceipt,
    HandoffBundle,
    HandoffChecklistItem,
)
from apps.api.app.domain.execution.receipt import generate_execution_receipt


class ExecutionProvider(ABC):
    """
    Abstract interface for application submission and handoff providers.
    """

    @abstractmethod
    async def prepare_execution(
        self,
        execution: ApplicationExecution,
        context: ExecutionContext,
    ) -> tuple[ExecutionReceipt, HandoffBundle | None]:
        """Prepare or initiate execution."""
        pass


class UserHandoffProvider(ExecutionProvider):
    """
    Standard provider for unsupported external portals.
    Prepares a structured manual handoff packet for candidate execution.
    Never automates browser or steals credentials.
    """

    async def prepare_execution(
        self,
        execution: ApplicationExecution,
        context: ExecutionContext,
    ) -> tuple[ExecutionReceipt, HandoffBundle | None]:
        job_url = context.get_job_url()
        pkg = context.package

        checklist: list[HandoffChecklistItem] = [
            HandoffChecklistItem(
                id=str(uuid4()),
                title="Open Application Portal",
                description="Navigate to the official external application site.",
                action_type="OPEN_URL",
                payload=job_url,
                completed=False,
            ),
            HandoffChecklistItem(
                id=str(uuid4()),
                title="Tailored Resume Prepared",
                description="Download and upload your tailored resume with verified claims.",
                action_type="DOWNLOAD_RESUME",
                payload=f"/api/v1/resumes/tailored/{pkg.tailored_resume_id}" if pkg.tailored_resume_id else None,
                completed=False,
            ),
        ]

        if pkg.cover_letter:
            checklist.append(
                HandoffChecklistItem(
                    id=str(uuid4()),
                    title="Copy Cover Letter",
                    description="Copy your customized, claim-backed cover letter.",
                    action_type="COPY_COVER_LETTER",
                    payload=pkg.cover_letter,
                    completed=False,
                )
            )

        for idx, ans in enumerate(pkg.application_answers, start=1):
            checklist.append(
                HandoffChecklistItem(
                    id=str(uuid4()),
                    title=f"Answer Q{idx}: {ans.question[:40]}...",
                    description=f"Paste verified response to: '{ans.question}'",
                    action_type="COPY_ANSWER",
                    payload=ans.answer,
                    completed=False,
                )
            )

        checklist.append(
            HandoffChecklistItem(
                id=str(uuid4()),
                title="Mark Application as Submitted",
                description="Confirm you have submitted the application on the external portal.",
                action_type="MARK_SUBMITTED",
                completed=False,
            )
        )

        formatted_answers = [
            {
                "question": a.question,
                "answer": a.answer,
                "type": a.question_type,
            }
            for a in pkg.application_answers
        ]

        bundle = HandoffBundle(
            application_url=job_url,
            cover_letter=pkg.cover_letter,
            answers=formatted_answers,
            resume_download_url=f"/api/v1/resumes/tailored/{pkg.tailored_resume_id}" if pkg.tailored_resume_id else None,
            checklist=checklist,
        )

        receipt = generate_execution_receipt(
            execution_id=execution.id,
            package_id=pkg.id,
            job_id=execution.job_id,
            user_id=execution.user_id,
            execution_mode="USER_HANDOFF",
            status="USER_HANDOFF",
            idempotency_key=execution.idempotency_key,
            evidence_type="NONE",
            details={"handoff_url": job_url, "item_count": len(checklist)},
        )

        return receipt, bundle


class MockAPIExecutionProvider(ExecutionProvider):
    """
    ₹0-compatible deterministic Mock API execution provider for testing and verified partner APIs.
    Simulates API submission without hitting real third-party services.
    """

    async def prepare_execution(
        self,
        execution: ApplicationExecution,
        context: ExecutionContext,
    ) -> tuple[ExecutionReceipt, HandoffBundle | None]:
        now = datetime.now(timezone.utc)
        pkg = context.package

        receipt = generate_execution_receipt(
            execution_id=execution.id,
            package_id=pkg.id,
            job_id=execution.job_id,
            user_id=execution.user_id,
            execution_mode="API",
            status="SUBMITTED",
            idempotency_key=execution.idempotency_key,
            evidence_type="API_RESPONSE",
            submitted_at=now,
            details={
                "partner_confirmation_id": f"PARTNER-CONF-{uuid4().hex[:8].upper()}",
                "provider": "MockAPIExecutionProvider",
                "api_endpoint": "https://api.mockats.example.com/v1/applications",
            },
        )
        return receipt, None
