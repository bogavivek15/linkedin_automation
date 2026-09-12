"""
CareerOS Phase 8 — Match Repository.

In-memory transactional store for job match records.
Follows existing JobRepository / TrustRepository pattern.
Upserts on (profile_id, job_id) for idempotency.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from apps.api.app.domain.matching.models import (
    MatchAgentOutput,
    MatchConfidence,
    SkillMatchDetail,
    SkillMatchStatus,
    SkillProvenance,
)


class MatchRepository:
    """
    Repository for Candidate-Job Match records.
    Provides in-memory transactional store with RLS-equivalent user isolation.
    """

    _matches: dict[str, dict[str, Any]] = {}  # match_id_str -> match_dict
    _index_profile_job: dict[str, str] = {}  # "profile_id:job_id" -> match_id_str

    @classmethod
    def reset_store(cls) -> None:
        """Helper for test isolation."""
        cls._matches.clear()
        cls._index_profile_job.clear()

    @classmethod
    async def save_match(cls, match: MatchAgentOutput, user_id: UUID) -> MatchAgentOutput:
        """
        Save or upsert a match record. Upserts on (profile_id, job_id) for idempotency.
        """
        composite_key = f"{match.profile_id}:{match.job_id}"
        now = datetime.now(timezone.utc).isoformat()

        # Check for existing match (upsert)
        existing_id = cls._index_profile_job.get(composite_key)
        if existing_id:
            match_id = existing_id
            # Preserve original id
            match = match.model_copy(update={"id": UUID(match_id)})
        else:
            match_id = str(match.id)

        doc = {
            "id": match.id,
            "profile_id": match.profile_id,
            "job_id": match.job_id,
            "user_id": user_id,
            "semantic_score": match.semantic_score,
            "skill_score": match.skill_score,
            "experience_score": match.experience_score,
            "location_score": match.location_score,
            "preference_score": match.preference_score,
            "overall_score": match.overall_score,
            "matched_skills": match.matched_skills,
            "missing_skills": match.missing_skills,
            "uncertain_skills": match.uncertain_skills,
            "skill_match_details": [d.model_dump(mode="json") for d in match.skill_match_details],
            "experience_match": match.experience_match,
            "location_match": match.location_match,
            "preference_match": match.preference_match,
            "work_mode_match": match.work_mode_match,
            "employment_type_match": match.employment_type_match,
            "hard_constraints_passed": match.hard_constraints_passed,
            "hard_constraint_failures": match.hard_constraint_failures,
            "recommended_resume_id": match.recommended_resume_id,
            "resume_changes": match.resume_changes,
            "verification_questions": match.verification_questions,
            "confidence": match.confidence.value,
            "explanation": match.explanation,
            "matching_version": match.matching_version,
            "calculated_at": match.calculated_at.isoformat() if match.calculated_at else now,
            "created_at": now if not existing_id else cls._matches.get(match_id, {}).get("created_at", now),
            "updated_at": now,
        }

        cls._matches[str(match.id)] = doc
        cls._index_profile_job[composite_key] = str(match.id)

        return match

    @classmethod
    async def get_match(cls, match_id: UUID, user_id: UUID) -> MatchAgentOutput | None:
        """Fetch a single match by ID enforcing user ownership."""
        doc = cls._matches.get(str(match_id))
        if not doc:
            return None
        if str(doc.get("user_id")) != str(user_id):
            return None
        return cls._dict_to_model(doc)

    @classmethod
    async def get_match_for_job(
        cls, profile_id: UUID, job_id: UUID, user_id: UUID
    ) -> MatchAgentOutput | None:
        """Fetch match for a specific profile+job pair."""
        composite_key = f"{profile_id}:{job_id}"
        match_id = cls._index_profile_job.get(composite_key)
        if not match_id:
            return None
        return await cls.get_match(UUID(match_id), user_id)

    @classmethod
    async def get_matches_for_profile(
        cls,
        profile_id: UUID,
        user_id: UUID,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[MatchAgentOutput]:
        """List all matches for a profile enforcing user ownership."""
        results: list[dict[str, Any]] = []

        for doc in cls._matches.values():
            if str(doc.get("profile_id")) == str(profile_id) and str(doc.get("user_id")) == str(user_id):
                results.append(doc)

        # Sort by overall_score descending
        results.sort(key=lambda x: float(x.get("overall_score", 0)), reverse=True)
        paginated = results[offset: offset + limit]

        return [cls._dict_to_model(d) for d in paginated]

    @classmethod
    async def delete_match(cls, match_id: UUID, user_id: UUID) -> bool:
        """Delete a match record enforcing user ownership."""
        doc = cls._matches.get(str(match_id))
        if not doc:
            return False
        if str(doc.get("user_id")) != str(user_id):
            return False

        composite_key = f"{doc['profile_id']}:{doc['job_id']}"
        cls._index_profile_job.pop(composite_key, None)
        del cls._matches[str(match_id)]
        return True

    @classmethod
    def _dict_to_model(cls, d: dict[str, Any]) -> MatchAgentOutput:
        """Convert stored dict back to MatchAgentOutput."""
        skill_details = []
        for sd in d.get("skill_match_details", []):
            skill_details.append(
                SkillMatchDetail(
                    job_skill=sd["job_skill"],
                    candidate_skill=sd.get("candidate_skill"),
                    status=SkillMatchStatus(sd["status"]),
                    provenance=SkillProvenance(sd.get("provenance", "UNKNOWN")),
                    is_required=sd.get("is_required", True),
                )
            )

        return MatchAgentOutput(
            id=d["id"],
            profile_id=d["profile_id"],
            job_id=d["job_id"],
            semantic_score=float(d["semantic_score"]),
            skill_score=float(d["skill_score"]),
            experience_score=float(d["experience_score"]),
            location_score=float(d["location_score"]),
            preference_score=float(d["preference_score"]),
            overall_score=float(d["overall_score"]),
            matched_skills=d.get("matched_skills", []),
            missing_skills=d.get("missing_skills", []),
            uncertain_skills=d.get("uncertain_skills", []),
            skill_match_details=skill_details,
            experience_match=d.get("experience_match", "UNKNOWN"),
            location_match=d.get("location_match", "UNKNOWN"),
            preference_match=d.get("preference_match", "UNKNOWN"),
            work_mode_match=d.get("work_mode_match", "UNKNOWN"),
            employment_type_match=d.get("employment_type_match", "UNKNOWN"),
            hard_constraints_passed=d.get("hard_constraints_passed", True),
            hard_constraint_failures=d.get("hard_constraint_failures", []),
            recommended_resume_id=d.get("recommended_resume_id"),
            resume_changes=d.get("resume_changes", []),
            verification_questions=d.get("verification_questions", []),
            confidence=MatchConfidence(d.get("confidence", "MEDIUM")),
            explanation=d.get("explanation", ""),
            matching_version=d.get("matching_version", "matching_v1.0"),
        )
