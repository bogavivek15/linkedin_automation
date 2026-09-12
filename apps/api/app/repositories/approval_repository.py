"""
CareerOS Phase 9.x — Approval Repository.

In-memory transactional store for human-in-the-loop approval requests.
Adheres to 022_approval_requests.sql with strict RLS user isolation.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from apps.api.app.domain.graph.models import ApprovalRequest, ApprovalStatus


class ApprovalRepository:
    """
    Repository for storing and resolving human-in-the-loop approval requests.
    """

    _approvals: dict[str, dict[str, Any]] = {}  # approval_id_str -> dict
    _index_run_job: dict[str, str] = {}  # f"{run_id}:{job_id}" -> approval_id_str

    @classmethod
    def reset_store(cls) -> None:
        """Helper for test isolation."""
        cls._approvals.clear()
        cls._index_run_job.clear()

    @classmethod
    async def save_approval(cls, approval: ApprovalRequest, user_id: UUID) -> ApprovalRequest:
        """
        Save or upsert an approval request.
        Upserts on (run_id, job_id) for idempotency.
        """
        composite_key = f"{approval.run_id}:{approval.job_id}"
        now = datetime.now(timezone.utc)

        existing_id = cls._index_run_job.get(composite_key)
        if existing_id:
            approval = approval.model_copy(update={"id": UUID(existing_id)})
            approval_id = existing_id
        else:
            approval_id = str(approval.id)

        doc = {
            "id": approval.id,
            "run_id": approval.run_id,
            "profile_id": approval.profile_id,
            "job_id": approval.job_id,
            "decision_id": approval.decision_id,
            "user_id": user_id,
            "status": approval.status,
            "requested_action": approval.requested_action,
            "reason": approval.reason,
            "expires_at": approval.expires_at,
            "created_at": approval.created_at or now,
            "resolved_at": approval.resolved_at,
            "resolved_by": approval.resolved_by,
            "job_title": approval.job_title,
            "company_name": approval.company_name,
            "match_score": approval.match_score,
            "trust_score": approval.trust_score,
            "risk_level": approval.risk_level,
            "decision_reasons": approval.decision_reasons,
            "action_type": approval.action_type,
            "why_matched": approval.why_matched,
            "resume_changes": approval.resume_changes,
            "uncertainties": approval.uncertainties,
            "risks": approval.risks,
            "evidence_citations": approval.evidence_citations,
        }

        cls._approvals[approval_id] = doc
        cls._index_run_job[composite_key] = approval_id
        return approval

    @classmethod
    async def get_approval(cls, approval_id: UUID, user_id: UUID) -> ApprovalRequest | None:
        """
        Retrieve approval by ID enforcing user isolation.
        """
        doc = cls._approvals.get(str(approval_id))
        if not doc or doc.get("user_id") != user_id:
            return None
        return ApprovalRequest(**doc)

    @classmethod
    async def list_approvals_for_user(
        cls,
        user_id: UUID,
        status: str | None = None,
    ) -> list[ApprovalRequest]:
        """
        List approval requests for user, optionally filtered by status.
        """
        results = [
            d for d in cls._approvals.values()
            if d.get("user_id") == user_id and (status is None or d.get("status") == status)
        ]
        results.sort(key=lambda d: d.get("created_at", datetime.min), reverse=True)
        return [ApprovalRequest(**d) for d in results]

    @classmethod
    async def list_pending(cls, user_id: UUID) -> list[ApprovalRequest]:
        """Convenience method to list pending approvals for a user."""
        return await cls.list_approvals_for_user(user_id, status=ApprovalStatus.PENDING.value)


    @classmethod
    async def update_approval_status(
        cls,
        approval_id: UUID,
        user_id: UUID,
        status: str,
        resolved_by: UUID,
    ) -> ApprovalRequest | None:
        """
        Update the status of an approval request (APPROVE / REJECT / CANCEL).
        """
        doc = cls._approvals.get(str(approval_id))
        if not doc or doc.get("user_id") != user_id:
            return None

        now = datetime.now(timezone.utc)
        doc["status"] = status
        doc["resolved_at"] = now
        doc["resolved_by"] = resolved_by

        return ApprovalRequest(**doc)

    @classmethod
    async def get_pending_for_run(
        cls,
        run_id: UUID,
        user_id: UUID,
    ) -> list[ApprovalRequest]:
        """
        Get all pending approval requests for a specific run.
        """
        results = [
            d for d in cls._approvals.values()
            if d.get("user_id") == user_id
            and d.get("run_id") == run_id
            and d.get("status") == ApprovalStatus.PENDING.value
        ]
        return [ApprovalRequest(**d) for d in results]

