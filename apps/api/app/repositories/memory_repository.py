"""
CareerOS Phase 14 — Career Memory Repository.

Persistence layer for persistent, categorized career memory items.
Strict multi-tenant isolation matching 026_learning_memory.sql.
"""

from typing import Any
from uuid import UUID

from apps.api.app.domain.memory.models import CareerMemoryRecord, MemoryCategory


class MemoryRepository:
    """
    Repository for persisting and querying persistent structured career memories.
    """

    _memories: dict[str, dict[str, Any]] = {}
    _index_user_cat_key: dict[str, str] = {}  # f"{user_id}:{category}:{key}" -> memory_id

    @classmethod
    def reset_store(cls) -> None:
        """Helper for test isolation."""
        cls._memories.clear()
        cls._index_user_cat_key.clear()

    @classmethod
    async def save_memory(
        cls,
        memory: CareerMemoryRecord,
        user_id: UUID,
    ) -> CareerMemoryRecord:
        """
        Save or upsert a CareerMemoryRecord.
        """
        mem_id = str(memory.id)
        user_str = str(user_id)
        composite_key = f"{user_str}:{memory.category}:{memory.key}"

        doc = {
            "id": mem_id,
            "user_id": user_str,
            "profile_id": str(memory.profile_id),
            "category": memory.category,
            "key": memory.key,
            "content": memory.content,
            "provenance": memory.provenance,
            "confidence": memory.confidence,
            "verification_status": memory.verification_status,
            "source": memory.source,
            "evidence_ref": memory.evidence_ref,
            "reason": memory.reason,
            "source_event": memory.source_event,
            "source_ref_id": str(memory.source_ref_id) if memory.source_ref_id else None,
            "metadata": memory.metadata,
            "created_at": memory.created_at,
            "updated_at": memory.updated_at,
            "_raw_model": memory,
        }

        cls._memories[mem_id] = doc
        cls._index_user_cat_key[composite_key] = mem_id
        return memory

    @classmethod
    async def get_memory(
        cls,
        memory_id: UUID | str,
        user_id: UUID,
    ) -> CareerMemoryRecord | None:
        """
        Retrieve memory by ID with user isolation.
        """
        doc = cls._memories.get(str(memory_id))
        if not doc or doc["user_id"] != str(user_id):
            return None
        return doc["_raw_model"]

    @classmethod
    async def get_by_key(
        cls,
        category: MemoryCategory,
        key: str,
        user_id: UUID,
    ) -> CareerMemoryRecord | None:
        """
        Retrieve memory by unique composite key (user, category, key).
        """
        composite = f"{user_id}:{category}:{key}"
        mem_id = cls._index_user_cat_key.get(composite)
        if not mem_id:
            return None
        return await cls.get_memory(mem_id, user_id)

    @classmethod
    async def list_memories(
        cls,
        user_id: UUID,
        category: MemoryCategory | None = None,
        profile_id: str | None = None,
    ) -> list[CareerMemoryRecord]:
        """
        List memories for user, optionally filtered by category and profile.
        """
        user_str = str(user_id)
        results: list[CareerMemoryRecord] = []
        for doc in cls._memories.values():
            if doc["user_id"] == user_str:
                if category and doc["category"] != category:
                    continue
                if profile_id and doc["profile_id"] != profile_id:
                    continue
                results.append(doc["_raw_model"])
        return sorted(results, key=lambda x: x.updated_at, reverse=True)

    @classmethod
    async def delete_memory(
        cls,
        memory_id: UUID | str,
        user_id: UUID,
    ) -> bool:
        """
        Delete memory item enforcing user ownership.
        """
        doc = cls._memories.get(str(memory_id))
        if not doc or doc["user_id"] != str(user_id):
            return False
        composite = f"{user_id}:{doc['category']}:{doc['key']}"
        cls._index_user_cat_key.pop(composite, None)
        cls._memories.pop(str(memory_id), None)
        return True
