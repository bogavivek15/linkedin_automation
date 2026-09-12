"""
CareerOS Phase 9 — Decision Repository.

In-memory transactional store for opportunity decision records.
Follows existing JobRepository / TrustRepository / MatchRepository pattern.
Upserts on (profile_id, job_id) for idempotency and prevents uncontrolled duplicate records.
Enforces RLS-equivalent user isolation.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from apps.api.app.services.decision.models import Decision


class DecisionRepository:
    """
    Repository for storing and retrieving deterministic CareerOS decisions.
    """

    _decisions: dict[str, dict[str, Any]] = {}  # decision_id_str -> decision_dict
    _index_profile_job: dict[str, str] = {}  # "profile_id:job_id" -> decision_id_str

    @classmethod
    def reset_store(cls) -> None:
        """Helper for test isolation."""
        cls._decisions.clear()
        cls._index_profile_job.clear()

    @classmethod
    async def save_decision(cls, decision: Decision, user_id: UUID) -> Decision:
        """
        Save or upsert a decision record.
        Upserts on (profile_id, job_id) to ensure idempotency.
        """
        composite_key = f"{decision.profile_id}:{decision.job_id}"
        now = datetime.now(timezone.utc)

        existing_id = cls._index_profile_job.get(composite_key)
        if existing_id:
            decision = decision.model_copy(update={"id": UUID(existing_id), "evaluated_at": now})
            decision_id = existing_id
        else:
            decision_id = str(decision.id)

        doc = {
            "id": decision.id,
            "profile_id": decision.profile_id,
            "job_id": decision.job_id,
            "match_id": decision.match_id,
            "trust_assessment_id": decision.trust_assessment_id,
            "user_id": user_id,
            "overall_score": decision.overall_score,
            "match_score": decision.match_score,
            "trust_score": decision.trust_score,
            "risk_level": decision.risk_level,
            "confidence": decision.confidence,
            "action": decision.action,
            "reasons": decision.reasons,
            "blocking_conditions": decision.blocking_conditions,
            "eligible_for_auto_apply": decision.eligible_for_auto_apply,
            "hard_constraints_passed": decision.hard_constraints_passed,
            "approval_required": decision.approval_required,
            "application_mode": decision.application_mode,
            "policy_version": decision.policy_version,
            "decision_version": decision.decision_version,
            "evaluated_at": decision.evaluated_at,
            "created_at": now,
            "updated_at": now,
        }

        cls._decisions[decision_id] = doc
        cls._index_profile_job[composite_key] = decision_id
        return decision

    @classmethod
    async def get_decision(cls, decision_id: UUID, user_id: UUID) -> Decision | None:
        """
        Get a specific decision by ID, enforcing user isolation.
        """
        doc = cls._decisions.get(str(decision_id))
        if not doc or doc.get("user_id") != user_id:
            return None
        return Decision(**{k: v for k, v in doc.items() if k not in ("user_id", "created_at", "updated_at")})

    get_decision_by_id = get_decision

    @classmethod
    async def get_decision_for_job(
        cls,
        profile_id: UUID,
        job_id: UUID,
        user_id: UUID,
    ) -> Decision | None:
        """
        Get the decision for a specific profile and job, enforcing user isolation.
        """
        composite_key = f"{profile_id}:{job_id}"
        decision_id = cls._index_profile_job.get(composite_key)
        if not decision_id:
            return None
        return await cls.get_decision(UUID(decision_id), user_id)

    @classmethod
    async def get_decisions_for_profile(
        cls,
        profile_id: UUID,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Decision]:
        """
        List decisions for a profile, sorted by overall_score descending.
        """
        results: list[dict[str, Any]] = []
        for doc in cls._decisions.values():
            if doc.get("profile_id") == profile_id and doc.get("user_id") == user_id:
                results.append(doc)

        results.sort(key=lambda d: d.get("overall_score", 0), reverse=True)
        sliced = results[offset : offset + limit]
        return [
            Decision(**{k: v for k, v in d.items() if k not in ("user_id", "created_at", "updated_at")})
            for d in sliced
        ]

    @classmethod
    async def delete_decision(cls, decision_id: UUID, user_id: UUID) -> None:
        """
        Delete a decision, enforcing user isolation.
        """
        doc = cls._decisions.get(str(decision_id))
        if doc and doc.get("user_id") == user_id:
            composite_key = f"{doc.get('profile_id')}:{doc.get('job_id')}"
            cls._index_profile_job.pop(composite_key, None)
            cls._decisions.pop(str(decision_id), None)
