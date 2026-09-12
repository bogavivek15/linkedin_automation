"""
CareerOS Phase 14 — Career Memory Write Policy & Verification Gates.

Enforces:
AI proposal -> Evidence check -> Deterministic validation -> User confirmation when necessary -> Persist.
Prohibits LLM from directly writing authoritative memory.
"""

from apps.api.app.core.errors import CareerOSError
from apps.api.app.domain.memory.models import (
    MemoryCategory,
    MemoryVerificationStatus,
)

CORE_FACT_CATEGORIES: set[MemoryCategory] = {
    "PROFILE",
    "SKILL",
    "EXPERIENCE",
    "EDUCATION",
    "CERTIFICATION",
}


class DirectAuthoritativeMemoryWriteError(CareerOSError):
    """Raised when an automated agent attempts to write authoritative memory without evidence/user verification."""

    def __init__(self, category: str, key: str):
        super().__init__(
            code="DIRECT_AUTHORITATIVE_WRITE_PROHIBITED",
            message=f"Direct authoritative write prohibited for {category}:{key}. Must go through AI_PROPOSED -> EVIDENCE_VALIDATED -> USER_CONFIRMED.",
            status_code=400,
        )


class MemoryWritePolicy:
    """
    Guards memory persistence against hallucination and unauthorized fact mutation.
    """

    @classmethod
    def validate_memory_write(
        cls,
        category: MemoryCategory,
        key: str,
        content: str,
        proposed_status: MemoryVerificationStatus,
        actor: str = "AI_AGENT",
        evidence_provided: bool = False,
    ) -> MemoryVerificationStatus:
        """
        Validate and return the allowable verification status for memory creation or update.
        """
        # Invariant 1: AI cannot directly assert AUTHORITATIVE or CONFIRMED status
        if actor != "USER" and proposed_status in ("AUTHORITATIVE", "USER_CONFIRMED", "STUDENT_CONFIRMED"):
            raise DirectAuthoritativeMemoryWriteError(category, key)

        # Invariant 2: If proposed by AI, restrict to non-authoritative tiers
        if actor != "USER":
            if proposed_status in ("INFERRED", "RECOMMENDED_LEARNING"):
                return proposed_status
            if evidence_provided:
                return "EVIDENCE_VALIDATED"
            return "AI_PROPOSED"

        # Invariant 3: Human candidate can confirm or write authoritative
        return proposed_status
