"""
CareerOS Phase 14 — Career Memory Service.

Orchestrates deterministic memory verification gates, evidence checks,
and contextual retrieval for applications, presence, and matching.
"""

from typing import Any
from uuid import UUID

from apps.api.app.domain.memory.models import (
    CareerMemoryRecord,
    MemoryCategory,
    MemoryVerificationStatus,
)
from apps.api.app.domain.memory.policy import MemoryWritePolicy
from apps.api.app.domain.memory.retrieval import CareerMemoryRetriever
from apps.api.app.repositories.memory_repository import MemoryRepository


class MemoryService:
    """
    Coordinates persistence and retrieval of structured persistent career memory.
    """

    async def record_memory(
        self,
        user_id: UUID,
        profile_id: str,
        category: MemoryCategory,
        key: str,
        content: str,
        provenance: str,
        confidence: float = 1.0,
        proposed_status: MemoryVerificationStatus = "AI_PROPOSED",
        actor: str = "AI_AGENT",
        evidence_provided: bool = False,
        source: str | None = None,
        evidence_ref: str | None = None,
        reason: str | None = None,
        source_event: str | None = None,
        source_ref_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CareerMemoryRecord:
        """
        Record or propose a structured career memory item, strictly applying MemoryWritePolicy.
        """
        effective_status = MemoryWritePolicy.validate_memory_write(
            category=category,
            key=key,
            content=content,
            proposed_status=proposed_status,
            actor=actor,
            evidence_provided=evidence_provided,
        )

        record = CareerMemoryRecord(
            user_id=str(user_id),
            profile_id=profile_id,
            category=category,
            key=key,
            content=content,
            provenance=provenance,
            confidence=confidence,
            verification_status=effective_status,
            source=source,
            evidence_ref=evidence_ref,
            reason=reason,
            source_event=source_event,
            source_ref_id=source_ref_id,
            metadata=metadata or {},
        )

        return await MemoryRepository.save_memory(record, user_id)

    async def confirm_memory(
        self,
        memory_id: str,
        user_id: UUID,
    ) -> CareerMemoryRecord | None:
        """
        Allows human candidate to confirm an AI-proposed or evidence-validated memory item.
        """
        record = await MemoryRepository.get_memory(memory_id, user_id)
        if not record:
            return None

        record.verification_status = "USER_CONFIRMED"
        return await MemoryRepository.save_memory(record, user_id)

    async def list_memories(
        self,
        user_id: UUID,
        category: MemoryCategory | None = None,
        profile_id: str | None = None,
    ) -> list[CareerMemoryRecord]:
        return await MemoryRepository.list_memories(user_id, category, profile_id)

    async def get_memory(
        self,
        memory_id: str,
        user_id: UUID,
    ) -> CareerMemoryRecord | None:
        return await MemoryRepository.get_memory(memory_id, user_id)

    async def delete_memory(
        self,
        memory_id: str,
        user_id: UUID,
    ) -> bool:
        return await MemoryRepository.delete_memory(memory_id, user_id)

    async def retrieve_for_application(
        self,
        user_id: UUID,
        profile_id: str | None = None,
    ) -> dict[str, list[CareerMemoryRecord]]:
        """
        Retrieve structured, evidence-grounded memory for application generation.
        """
        memories = await MemoryRepository.list_memories(user_id, profile_id=profile_id)
        return CareerMemoryRetriever.retrieve_for_application(memories)

    async def retrieve_for_presence(
        self,
        user_id: UUID,
        profile_id: str | None = None,
    ) -> list[CareerMemoryRecord]:
        """
        Retrieve verified achievements, projects, and insights for professional presence posts.
        """
        memories = await MemoryRepository.list_memories(user_id, profile_id=profile_id)
        return CareerMemoryRetriever.retrieve_for_presence(memories)
