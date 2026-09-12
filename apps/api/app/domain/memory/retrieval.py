"""
CareerOS Phase 14 — Career Memory Retrieval Engine.

Retrieves and organizes persistent structured career memory for downstream systems:
- Job matching (SKILL, PREFERENCE, GOAL)
- Application preparation (PROJECT, EXPERIENCE, CERTIFICATION)
- Professional presence (PROJECT, EXPERIENCE, INSIGHT, PRESENCE)
- Career insights (OUTCOME, FEEDBACK, INSIGHT)
"""

from apps.api.app.domain.memory.models import (
    CareerMemoryRecord,
    MemoryCategory,
    MemoryVerificationStatus,
)


class CareerMemoryRetriever:
    """
    Categorical and context-aware retriever over candidate memory records.
    """

    @classmethod
    def filter_memories(
        cls,
        memories: list[CareerMemoryRecord],
        categories: list[MemoryCategory] | None = None,
        min_confidence: float = 0.0,
        allowed_statuses: set[MemoryVerificationStatus] | None = None,
    ) -> list[CareerMemoryRecord]:
        """
        Filter memories by category, confidence threshold, and verification status.
        """
        results: list[CareerMemoryRecord] = []
        for m in memories:
            if categories and m.category not in categories:
                continue
            if m.confidence < min_confidence:
                continue
            if allowed_statuses and m.verification_status not in allowed_statuses:
                continue
            results.append(m)
        return sorted(results, key=lambda x: (x.confidence, x.updated_at), reverse=True)

    @classmethod
    def retrieve_for_application(
        cls,
        memories: list[CareerMemoryRecord],
    ) -> dict[str, list[CareerMemoryRecord]]:
        """
        Retrieve evidence-grounded records for application tailoring.
        Strictly excludes UNVERIFIED or low-confidence records.
        """
        verified = cls.filter_memories(
            memories,
            categories=["PROJECT", "EXPERIENCE", "SKILL", "CERTIFICATION", "EDUCATION"],
            min_confidence=0.7,
            allowed_statuses={"EVIDENCE_VALIDATED", "USER_CONFIRMED", "AUTHORITATIVE"},
        )
        grouped: dict[str, list[CareerMemoryRecord]] = {
            "projects": [m for m in verified if m.category == "PROJECT"],
            "experiences": [m for m in verified if m.category == "EXPERIENCE"],
            "skills": [m for m in verified if m.category == "SKILL"],
            "credentials": [m for m in verified if m.category in ("CERTIFICATION", "EDUCATION")],
        }
        return grouped

    @classmethod
    def retrieve_for_presence(
        cls,
        memories: list[CareerMemoryRecord],
    ) -> list[CareerMemoryRecord]:
        """
        Retrieve verified accomplishments, projects, and insights for professional content.
        """
        return cls.filter_memories(
            memories,
            categories=["PROJECT", "EXPERIENCE", "INSIGHT", "PRESENCE"],
            min_confidence=0.8,
            allowed_statuses={"EVIDENCE_VALIDATED", "USER_CONFIRMED", "AUTHORITATIVE"},
        )
