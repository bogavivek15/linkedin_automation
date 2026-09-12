"""
CareerOS Phase 14 — Career Memory / Persistent Knowledge System Domain Models.

Strongly typed models for 13 persistent memory categories, multi-tiered verification statuses,
provenance tracking, and multi-modal career knowledge.
"""

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

MemoryCategory = Literal[
    "PROFILE",
    "SKILL",
    "PROJECT",
    "EXPERIENCE",
    "EDUCATION",
    "CERTIFICATION",
    "PREFERENCE",
    "GOAL",
    "APPLICATION",
    "OUTCOME",
    "FEEDBACK",
    "INSIGHT",
    "PRESENCE",
    "LEARNING_GAP",
    "MILESTONE",
    "NETWORK_ACTIVITY",
]

MemoryVerificationStatus = Literal[
    "UNVERIFIED",
    "AI_PROPOSED",
    "INFERRED",
    "RECOMMENDED_LEARNING",
    "EVIDENCE_VALIDATED",
    "STUDENT_CONFIRMED",
    "USER_CONFIRMED",
    "AUTHORITATIVE",
]


class CareerMemoryRecord(BaseModel):
    """
    Persistent, structured career memory item containing provenance and verification state.
    Never promotes AI inference directly to a verified qualification.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    profile_id: str
    category: MemoryCategory
    key: str
    content: str
    provenance: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    verification_status: MemoryVerificationStatus = "AI_PROPOSED"
    source: str | None = None
    evidence_ref: str | None = None
    reason: str | None = None
    source_event: str | None = None
    source_ref_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_verified(self) -> bool:
        """True only if confirmed by candidate, evidence-validated, or authoritative."""
        return self.verification_status in (
            "AUTHORITATIVE",
            "USER_CONFIRMED",
            "STUDENT_CONFIRMED",
            "EVIDENCE_VALIDATED",
        )
