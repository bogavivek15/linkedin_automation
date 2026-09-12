import logging
from typing import Optional
from apps.api.app.core.errors import CareerOSError
from apps.api.app.domain.presence.models import PublicationMode

logger = logging.getLogger("careeros.presence")

class PresencePolicy:
    """Policy rules for Presence Agent validation and publishing logic."""

    @staticmethod
    def validate_content_grounding(title: str, content_body: str, grounding_evidence_ids: list[str]) -> bool:
        """
        Ensures content is strictly backed by user memory (experiences, skills).
        """
        if not grounding_evidence_ids or len(grounding_evidence_ids) == 0:
            logger.warning(f"Failed grounding policy: No evidence provided for '{title}'.")
            raise CareerOSError(
                code="PRESENCE_GROUNDING_FAILED",
                message="Post must be grounded in at least one verified memory item.",
                status_code=400,
            )
        
        # In a full implementation, this could use an LLM or vector comparison 
        # to ensure the content doesn't hallucinate beyond the evidence.
        return True

    @staticmethod
    def calculate_quality_score(content_body: str, evidence_count: int) -> float:
        """
        Heuristic to assign a quality score to the generated post.
        """
        length = len(content_body)
        if length < 50:
            return 0.2
        elif length > 3000:
            return 0.5
        
        base_score = 0.7
        evidence_bonus = min(0.3, evidence_count * 0.1)
        return min(1.0, base_score + evidence_bonus)

    @staticmethod
    def resolve_publication_mode(requested_mode: PublicationMode, has_authorized_oauth: bool) -> PublicationMode:
        """
        Resolves the final publication mode based on oauth status and request.
        """
        if requested_mode == PublicationMode.LIVE:
            if not has_authorized_oauth:
                logger.warning("Requested LIVE mode but user lacks OAuth. Falling back to USER_HANDOFF.")
                return PublicationMode.USER_HANDOFF
            return PublicationMode.LIVE
        
        return requested_mode
