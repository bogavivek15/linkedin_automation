import logging
from typing import Optional
from apps.api.app.domain.presence.models import PresencePost, ContentType
from apps.api.app.domain.presence.generator import PresenceContentGenerator
from apps.api.app.domain.presence.policy import PresencePolicy
from apps.api.app.repositories.memory_repository import MemoryRepository
from apps.api.app.repositories.presence_repository import PresenceRepository

logger = logging.getLogger("careeros.presence.scheduler")

class PresenceScheduler:
    """Manages scheduling and coordination of Presence Agent generation."""

    def schedule_daily_post(self, user_id: str, profile_id: str, context_text: str):
        """
        In a full implementation, this registers a recurring cron job or celery task.
        For now, it simply logs the scheduling intent.
        """
        logger.info(f"Scheduled daily presence post check for user {user_id}")

    async def run_presence_generation(
        self, user_id: str, profile_id: str, context_text: str
    ) -> PresencePost:
        """
        Executes the Presence Agent workflow to draft a new post based on memory.
        """
        import uuid
        user_uuid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id

        # 1. Fetch recent memories to ground the post
        memories = await MemoryRepository.list_memories(user_id=user_uuid, profile_id=profile_id)
        
        # In a real scenario we pick the most relevant unused memory
        target_memory = memories[0] if memories else {"title": "Career Update", "type": "Milestone"}
        
        if hasattr(target_memory, "model_dump"):
            target_memory = target_memory.model_dump()
        
        # 2. Draft the post via Gemini
        post = PresenceContentGenerator.draft_post_from_memory(
            user_id=str(user_id),
            profile_id=profile_id,
            memory=target_memory,
            content_type=ContentType.LINKEDIN_POST
        )
        
        # 3. Apply Quality Policy
        post.quality_score = PresencePolicy.calculate_quality_score(
            content_body=post.content_body,
            evidence_count=len(post.grounding_evidence_ids)
        )
        
        # 4. Generate the accompanying Image via Gemini Imagen
        image_uri = PresenceContentGenerator.generate_image_for_post(post)
        if image_uri:
            post.image_url = image_uri
            
        # 5. Persist to DB (as PENDING_REVIEW)
        # Assuming PresenceRepository handles this; we mock it if needed
        saved_post = await PresenceRepository.save_post(post, user_uuid)
        
        return saved_post

# Singleton instance for the orchestrator
presence_scheduler = PresenceScheduler()
