"""
CareerOS Phase 12 — Application Lifecycle Repository.

Persistence layer for application lifecycle records, auditable status transitions,
and follow-up recommendations. Strict multi-tenant isolation matching 025_application_lifecycle.sql.
"""

from typing import Any
from uuid import UUID

from apps.api.app.domain.application_lifecycle.models import (
    FollowUpRecommendation,
    LifecycleRecord,
    StatusTransition,
)


class LifecycleRepository:
    """
    Repository for persisting and querying persistent application lifecycle states and history.
    """

    _lifecycles: dict[str, dict[str, Any]] = {}       # lifecycle_id -> dict
    _index_user_app: dict[str, str] = {}              # f"{user_id}:{application_id}" -> lifecycle_id
    _transitions: dict[str, list[dict[str, Any]]] = {} # lifecycle_id -> list[transition_dict]
    _follow_ups: dict[str, list[dict[str, Any]]] = {}  # lifecycle_id -> list[follow_up_dict]

    @classmethod
    def reset_store(cls) -> None:
        """Helper for test isolation."""
        cls._lifecycles.clear()
        cls._index_user_app.clear()
        cls._transitions.clear()
        cls._follow_ups.clear()

    @classmethod
    async def save_lifecycle(
        cls,
        record: LifecycleRecord,
        user_id: UUID,
    ) -> LifecycleRecord:
        """
        Save or upsert a LifecycleRecord enforcing user isolation.
        """
        rec_id = str(record.id)
        user_str = str(user_id)
        index_key = f"{user_str}:{record.application_id}"

        doc = {
            "id": rec_id,
            "application_id": str(record.application_id),
            "user_id": user_str,
            "job_id": str(record.job_id),
            "current_status": record.current_status,
            "last_transition_at": record.last_transition_at,
            "metadata": record.metadata,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
            "_raw_model": record,
        }

        cls._lifecycles[rec_id] = doc
        cls._index_user_app[index_key] = rec_id
        return record

    @classmethod
    async def get_lifecycle(
        cls,
        lifecycle_id: UUID | str,
        user_id: UUID,
    ) -> LifecycleRecord | None:
        """
        Retrieve lifecycle by ID with user isolation.
        """
        doc = cls._lifecycles.get(str(lifecycle_id))
        if not doc or doc["user_id"] != str(user_id):
            return None
        rec = doc["_raw_model"]
        rec.transitions = await cls.get_transitions(lifecycle_id, user_id)
        rec.follow_up_recommendations = await cls.get_follow_ups(lifecycle_id, user_id)
        return rec

    @classmethod
    async def get_by_application_id(
        cls,
        application_id: UUID | str,
        user_id: UUID,
    ) -> LifecycleRecord | None:
        """
        Retrieve lifecycle by application ID with user isolation.
        """
        key = f"{user_id}:{application_id}"
        rec_id = cls._index_user_app.get(key)
        if not rec_id:
            return None
        return await cls.get_lifecycle(rec_id, user_id)

    @classmethod
    async def list_lifecycles_for_user(
        cls,
        user_id: UUID,
    ) -> list[LifecycleRecord]:
        """List all lifecycle records for user."""
        return await cls.list_lifecycles(user_id)

    @classmethod
    async def list_lifecycles(
        cls,
        user_id: UUID,
        status: str | None = None,
    ) -> list[LifecycleRecord]:
        """
        List all lifecycle records for authenticated user.
        """
        user_str = str(user_id)
        results: list[LifecycleRecord] = []
        for doc in cls._lifecycles.values():
            if doc["user_id"] == user_str:
                if status and doc["current_status"] != status:
                    continue
                rec = doc["_raw_model"]
                results.append(rec)
        return sorted(results, key=lambda x: x.last_transition_at, reverse=True)

    @classmethod
    async def add_transition(
        cls,
        transition: StatusTransition,
        user_id: UUID,
    ) -> StatusTransition:
        """
        Append an auditable transition record.
        """
        lic_id = str(transition.lifecycle_id)
        if lic_id not in cls._transitions:
            cls._transitions[lic_id] = []

        cls._transitions[lic_id].append({
            "id": str(transition.id),
            "lifecycle_id": lic_id,
            "user_id": str(user_id),
            "from_status": transition.from_status,
            "to_status": transition.to_status,
            "evidence_type": transition.evidence_type,
            "evidence_details": transition.evidence_details,
            "actor": transition.actor,
            "notes": transition.notes,
            "created_at": transition.created_at,
            "_raw_model": transition,
        })
        return transition

    @classmethod
    async def get_transitions(
        cls,
        lifecycle_id: UUID | str,
        user_id: UUID,
    ) -> list[StatusTransition]:
        """
        Retrieve all transitions for a lifecycle record.
        """
        lic_id = str(lifecycle_id)
        raw_list = cls._transitions.get(lic_id, [])
        return [t["_raw_model"] for t in raw_list if t["user_id"] == str(user_id)]

    @classmethod
    async def add_follow_up(
        cls,
        recommendation: FollowUpRecommendation,
        user_id: UUID,
    ) -> FollowUpRecommendation:
        """
        Save follow-up recommendation draft.
        """
        lic_id = str(recommendation.lifecycle_id)
        if lic_id not in cls._follow_ups:
            cls._follow_ups[lic_id] = []

        cls._follow_ups[lic_id].append({
            "id": str(recommendation.id),
            "lifecycle_id": lic_id,
            "user_id": str(user_id),
            "_raw_model": recommendation,
        })
        return recommendation

    @classmethod
    async def update_follow_up(
        cls,
        recommendation: FollowUpRecommendation,
        user_id: UUID,
    ) -> FollowUpRecommendation:
        """
        Update status or notes on a follow-up recommendation.
        """
        lic_id = str(recommendation.lifecycle_id)
        items = cls._follow_ups.get(lic_id, [])
        for item in items:
            if item["id"] == str(recommendation.id) and item["user_id"] == str(user_id):
                item["_raw_model"] = recommendation
                return recommendation
        return recommendation

    @classmethod
    async def get_follow_ups(
        cls,
        lifecycle_id: UUID | str,
        user_id: UUID,
    ) -> list[FollowUpRecommendation]:
        """
        Retrieve all follow-up recommendations for a lifecycle record.
        """
        lic_id = str(lifecycle_id)
        raw_list = cls._follow_ups.get(lic_id, [])
        return [f["_raw_model"] for f in raw_list if f["user_id"] == str(user_id)]
