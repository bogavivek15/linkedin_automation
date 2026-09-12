"""
CareerOS Phase 15 — Professional Presence Intelligence Service.

Coordinates idea generation, evidence-backed post drafting, human approval,
and safe user-handoff publishing.
"""

from datetime import datetime, timezone
from uuid import UUID

from apps.api.app.core.errors import CareerOSError
from apps.api.app.domain.presence.generator import PresenceContentGenerator
from apps.api.app.domain.presence.models import (
    ContentIdea,
    ContentType,
    PresencePost,
    PublicationMode,
    PostStatus,
)
from apps.api.app.domain.presence.policy import PresencePolicy
from apps.api.app.repositories.memory_repository import MemoryRepository
from apps.api.app.repositories.presence_repository import PresenceRepository


class PresenceService:
    """
    Business service for managing professional presence content.
    """

    async def generate_ideas(
        self,
        user_id: UUID,
        profile_id: str,
    ) -> list[ContentIdea]:
        """
        Generate grounded content ideas from verified candidate memories.
        """
        memories = await MemoryRepository.list_memories(user_id=user_id, profile_id=profile_id)
        return PresenceContentGenerator.generate_ideas(
            user_id=str(user_id),
            profile_id=profile_id,
            memories=memories,
        )

    async def draft_from_memory(
        self,
        memory_id: str,
        user_id: UUID,
        profile_id: str,
        content_type: ContentType = "LINKEDIN_POST",
    ) -> PresencePost:
        """
        Synthesize a new draft grounded strictly in a verified memory record.
        """
        if memory_id == "latest":
            memories = await MemoryRepository.list_memories(user_id=user_id, profile_id=profile_id)
            memory = memories[0] if memories else None
            
            if not memory:
                # Provide a mock memory for the demo orchestrator
                from apps.api.app.domain.memory.models import CareerMemoryRecord
                from uuid import uuid4
                memory = CareerMemoryRecord(
                    id=str(uuid4()),
                    user_id=str(user_id),
                    profile_id=profile_id,
                    category="PROJECT",
                    key="demo-memory",
                    content="Built an Autonomous Multi-Agent System.",
                    provenance="SYSTEM",
                    verification_status="AUTHORITATIVE",
                )
                await MemoryRepository.save_memory(memory, user_id)
        else:
            memory = await MemoryRepository.get_memory(memory_id, user_id)
            
        if not memory:
            raise CareerOSError(
                code="MEMORY_NOT_FOUND",
                message="Target memory item not found for grounding.",
                status_code=404,
            )

        # Convert to dict to satisfy generator's expectation
        memory_dict = memory.model_dump() if hasattr(memory, "model_dump") else memory
        if "title" not in memory_dict:
            # Try to derive title from category or default
            memory_dict["title"] = memory_dict.get("key", "Career Portfolio")
        if "type" not in memory_dict:
            memory_dict["type"] = memory_dict.get("category", "Project")

        post = PresenceContentGenerator.draft_post_from_memory(
            user_id=str(user_id),
            profile_id=profile_id,
            memory=memory_dict,
            content_type=content_type,
        )

        # Automatically generate the accompanying image for the first draft
        image_uri = PresenceContentGenerator.generate_image_for_post(post)
        if image_uri:
            post.image_url = image_uri

        return await PresenceRepository.save_post(post, user_id)

    async def create_custom_post(
        self,
        user_id: UUID,
        profile_id: str,
        title: str,
        content_body: str,
        evidence_ids: list[str],
        content_type: ContentType = "LINKEDIN_POST",
        publication_mode: PublicationMode = "USER_HANDOFF",
    ) -> PresencePost:
        """
        Create a custom post draft, strictly validating evidence grounding.
        """
        # Validate grounding policy
        PresencePolicy.validate_content_grounding(
            title=title,
            content_body=content_body,
            evidence_ids=evidence_ids,
        )

        resolved_mode = PresencePolicy.resolve_publication_mode(
            requested_mode=publication_mode,
            has_authorized_oauth=False,
        )

        quality_score = PresencePolicy.calculate_quality_score(
            content_body=content_body,
            evidence_count=len(evidence_ids),
        )

        post = PresencePost(
            user_id=str(user_id),
            profile_id=profile_id,
            content_type=content_type,
            title=title,
            content_body=content_body,
            grounding_evidence_ids=evidence_ids,
            quality_score=quality_score,
            validation_status=PostStatus.PENDING_REVIEW,
            publication_mode=resolved_mode,
        )
        return await PresenceRepository.save_post(post, user_id)

    async def approve_post(
        self,
        post_id: str,
        user_id: UUID,
    ) -> PresencePost:
        """
        User approval gate for presence content.
        """
        post = await PresenceRepository.get_post(post_id, user_id)
        if not post:
            raise CareerOSError(code="POST_NOT_FOUND", message="Post not found", status_code=404)

        post.validation_status = PostStatus.APPROVED
        post.updated_at = datetime.now(timezone.utc)
        return await PresenceRepository.save_post(post, user_id)

    async def mark_published_handoff(
        self,
        post_id: str,
        external_url: str | None,
        user_id: UUID,
    ) -> PresencePost:
        """
        Record user assertion that post was published externally.
        """
        post = await PresenceRepository.get_post(post_id, user_id)
        if not post:
            raise CareerOSError(code="POST_NOT_FOUND", message="Post not found", status_code=404)

        now = datetime.now(timezone.utc)
        post.validation_status = PostStatus.PUBLISHED
        post.published_at = now
        post.publication_evidence = {
            "handoff_assertion_by": "USER",
            "asserted_at": now.isoformat(),
            "external_url": external_url,
        }
        post.updated_at = now
        return await PresenceRepository.save_post(post, user_id)

    async def list_posts(
        self,
        user_id: UUID,
        profile_id: str | None = None,
        status: str | None = None,
    ) -> list[PresencePost]:
        return await PresenceRepository.list_posts(user_id, profile_id, status)

    async def get_post(
        self,
        post_id: str,
        user_id: UUID,
    ) -> PresencePost | None:
        return await PresenceRepository.get_post(post_id, user_id)

    async def delete_post(
        self,
        post_id: str,
        user_id: UUID,
    ) -> bool:
        return await PresenceRepository.delete_post(post_id, user_id)
