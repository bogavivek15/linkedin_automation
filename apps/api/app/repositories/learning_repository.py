"""
CareerOS Phase 13 — Learning & Feedback Loop Repository.

Persistence layer for career outcomes, empirical patterns, and actionable insights.
Strict multi-tenant isolation matching 026_learning_memory.sql.
"""

from typing import Any
from uuid import UUID

from apps.api.app.domain.learning.models import (
    CareerInsight,
    CareerOutcome,
    CareerPattern,
)


class LearningRepository:
    """
    Repository for storing and querying outcomes, patterns, and insights.
    """

    _outcomes: dict[str, dict[str, Any]] = {}
    _patterns: dict[str, dict[str, Any]] = {}
    _insights: dict[str, dict[str, Any]] = {}

    @classmethod
    def reset_store(cls) -> None:
        """Helper for test isolation."""
        cls._outcomes.clear()
        cls._patterns.clear()
        cls._insights.clear()

    @classmethod
    async def save_outcome(cls, outcome: CareerOutcome, user_id: UUID) -> CareerOutcome:
        user_str = str(user_id)
        doc = {
            "id": outcome.id,
            "user_id": user_str,
            "profile_id": outcome.profile_id,
            "job_id": outcome.job_id,
            "application_id": outcome.application_id,
            "outcome_type": outcome.outcome_type,
            "resume_id": outcome.resume_id,
            "tailored_resume_id": outcome.tailored_resume_id,
            "match_score": outcome.match_score,
            "trust_score": outcome.trust_score,
            "notes": outcome.notes,
            "extracted_skill_gaps": outcome.extracted_skill_gaps,
            "created_at": outcome.created_at,
            "_raw_model": outcome,
        }
        cls._outcomes[outcome.id] = doc
        return outcome

    @classmethod
    async def list_outcomes(cls, user_id: UUID, profile_id: str | None = None) -> list[CareerOutcome]:
        user_str = str(user_id)
        res = [
            d["_raw_model"]
            for d in cls._outcomes.values()
            if d["user_id"] == user_str and (not profile_id or d["profile_id"] == profile_id)
        ]
        return sorted(res, key=lambda x: x.created_at, reverse=True)

    @classmethod
    async def save_patterns(cls, patterns: list[CareerPattern], user_id: UUID) -> list[CareerPattern]:
        user_str = str(user_id)
        for p in patterns:
            cls._patterns[p.id] = {
                "id": p.id,
                "user_id": user_str,
                "profile_id": p.profile_id,
                "pattern_type": p.pattern_type,
                "summary": p.summary,
                "confidence": p.confidence,
                "evidence_sample_count": p.evidence_sample_count,
                "evidence_details": p.evidence_details,
                "created_at": p.created_at,
                "updated_at": p.updated_at,
                "_raw_model": p,
            }
        return patterns

    @classmethod
    async def list_patterns(cls, user_id: UUID, profile_id: str | None = None) -> list[CareerPattern]:
        user_str = str(user_id)
        res = [
            d["_raw_model"]
            for d in cls._patterns.values()
            if d["user_id"] == user_str and (not profile_id or d["profile_id"] == profile_id)
        ]
        return sorted(res, key=lambda x: x.created_at, reverse=True)

    @classmethod
    async def save_insights(cls, insights: list[CareerInsight], user_id: UUID) -> list[CareerInsight]:
        user_str = str(user_id)
        for ins in insights:
            cls._insights[ins.id] = {
                "id": ins.id,
                "user_id": user_str,
                "profile_id": ins.profile_id,
                "category": ins.category,
                "severity": ins.severity,
                "title": ins.title,
                "description": ins.description,
                "actionable_recommendation": ins.actionable_recommendation,
                "supporting_pattern_ids": ins.supporting_pattern_ids,
                "dismissed": ins.dismissed,
                "created_at": ins.created_at,
                "_raw_model": ins,
            }
        return insights

    @classmethod
    async def list_insights(
        cls,
        user_id: UUID,
        profile_id: str | None = None,
        include_dismissed: bool = False,
    ) -> list[CareerInsight]:
        user_str = str(user_id)
        res = [
            d["_raw_model"]
            for d in cls._insights.values()
            if d["user_id"] == user_str
            and (not profile_id or d["profile_id"] == profile_id)
            and (include_dismissed or not d["dismissed"])
        ]
        return sorted(res, key=lambda x: x.created_at, reverse=True)

    @classmethod
    async def dismiss_insight(cls, insight_id: str, user_id: UUID) -> bool:
        doc = cls._insights.get(str(insight_id))
        if not doc or doc["user_id"] != str(user_id):
            return False
        doc["dismissed"] = True
        doc["_raw_model"].dismissed = True
        return True
