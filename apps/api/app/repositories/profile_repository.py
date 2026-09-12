"""
CareerOS Phase 8 — Profile Repository.

In-memory transactional store for career profiles, preferences, and profile skills.
Follows the existing JobRepository / TrustRepository pattern for ₹0 test/demo execution.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from apps.api.app.domain.matching.models import (
    CandidateProfile,
    CandidateSkill,
    ProfileSkillRecord,
    SkillProvenance,
    UserPreferencesRecord,
)


class ProfileRepository:
    """
    Repository for Career Profiles, User Preferences, and Profile Skills.
    Provides in-memory store for zero-dependency test/demo execution.
    """

    _profiles: dict[str, dict[str, Any]] = {}
    _preferences: dict[str, dict[str, Any]] = {}  # profile_id_str -> prefs
    _profile_skills: dict[str, list[dict[str, Any]]] = {}  # profile_id_str -> skills

    @classmethod
    def reset_store(cls) -> None:
        """Helper for test isolation."""
        cls._profiles.clear()
        cls._preferences.clear()
        cls._profile_skills.clear()

    @classmethod
    async def save_profile(
        cls,
        profile_id: UUID,
        user_id: UUID,
        full_name: str = "",
        headline: str = "",
        career_summary: str = "",
        location: str = "",
        experience: list[dict] | None = None,
        education: list[dict] | None = None,
        total_years_experience: float | None = None,
    ) -> dict[str, Any]:
        """Save or update a career profile."""
        pid = str(profile_id)
        now = datetime.now(timezone.utc).isoformat()

        doc = {
            "id": profile_id,
            "user_id": user_id,
            "full_name": full_name,
            "headline": headline,
            "career_summary": career_summary,
            "location": location,
            "experience": experience or [],
            "education": education or [],
            "total_years_experience": total_years_experience,
            "created_at": now,
            "updated_at": now,
        }
        cls._profiles[pid] = doc
        return doc

    @classmethod
    async def get_profile_by_user_id(cls, user_id: UUID) -> dict[str, Any] | None:
        """Get profile by user_id with ownership enforcement."""
        for doc in cls._profiles.values():
            if doc["user_id"] == user_id:
                return doc
        return None

    @classmethod
    async def get_profile(cls, profile_id: UUID, user_id: UUID) -> dict[str, Any] | None:
        """Get profile by ID enforcing user ownership."""
        doc = cls._profiles.get(str(profile_id))
        if not doc:
            return None
        if doc["user_id"] != user_id:
            return None
        return doc

    @classmethod
    async def save_preferences(cls, prefs: UserPreferencesRecord) -> UserPreferencesRecord:
        """Save or update user preferences."""
        pid = str(prefs.profile_id)
        cls._preferences[pid] = prefs.model_dump(mode="json")
        return prefs

    @classmethod
    async def get_preferences(cls, profile_id: UUID, user_id: UUID) -> UserPreferencesRecord | None:
        """Get preferences by profile_id enforcing user ownership."""
        pid = str(profile_id)
        doc = cls._preferences.get(pid)
        if not doc:
            return None
        if str(doc.get("user_id")) != str(user_id):
            return None
        return UserPreferencesRecord(**doc)

    @classmethod
    async def save_profile_skill(cls, skill: ProfileSkillRecord) -> ProfileSkillRecord:
        """Add or update a skill on a profile."""
        pid = str(skill.profile_id)
        if pid not in cls._profile_skills:
            cls._profile_skills[pid] = []
        norm = skill.normalized_name.lower()
        for i, existing in enumerate(cls._profile_skills[pid]):
            if existing.get("normalized_name", "").lower() == norm:
                cls._profile_skills[pid][i] = skill.model_dump(mode="json")
                return skill
        cls._profile_skills[pid].append(skill.model_dump(mode="json"))
        return skill

    add_skill = save_profile_skill

    @classmethod
    async def get_profile_skills(cls, profile_id: UUID, user_id: UUID) -> list[ProfileSkillRecord]:
        """Get all skills for a profile enforcing user ownership."""
        pid = str(profile_id)

        # Verify ownership through profile
        profile = cls._profiles.get(pid)
        if profile and str(profile["user_id"]) != str(user_id):
            return []

        skill_docs = cls._profile_skills.get(pid, [])
        return [ProfileSkillRecord(**doc) for doc in skill_docs]

    @classmethod
    async def build_candidate_profile(
        cls,
        profile_id: UUID,
        user_id: UUID,
        resume_ids: list[str] | None = None,
        resume_texts: dict[str, str] | None = None,
        resume_skills: dict[str, list[str]] | None = None,
    ) -> CandidateProfile | None:
        """
        Build the CandidateProfile aggregate from stored data.
        This is NOT a new table — it's an in-memory aggregate for matching.
        """
        profile = await cls.get_profile(profile_id, user_id)
        if not profile:
            return None

        prefs = await cls.get_preferences(profile_id, user_id)
        skill_records = await cls.get_profile_skills(profile_id, user_id)

        candidate_skills: list[CandidateSkill] = []
        for sr in skill_records:
            prov_map = {
                "VERIFIED": SkillProvenance.VERIFIED,
                "STUDENT_CONFIRMED": SkillProvenance.STUDENT_CONFIRMED,
                "INFERRED": SkillProvenance.INFERRED,
            }
            prov = prov_map.get(sr.verified_status.upper(), SkillProvenance.UNKNOWN)

            candidate_skills.append(
                CandidateSkill(
                    name=sr.skill_name,
                    normalized_name=sr.normalized_name,
                    proficiency=sr.proficiency,
                    years_experience=sr.years_experience,
                    provenance=prov,
                    source=sr.source,
                )
            )

        r_ids = list(resume_ids) if resume_ids else []
        r_texts = dict(resume_texts) if resume_texts else {}
        r_skills = dict(resume_skills) if resume_skills else {}

        if not r_ids:
            from apps.api.app.repositories.resume_repository import ResumeRepository
            for r_id_str, r_doc in ResumeRepository._resumes.items():
                if str(r_doc.get("user_id")) == str(user_id) or str(r_doc.get("profile_id")) == str(profile_id):
                    r_ids.append(r_id_str)
                    r_texts[r_id_str] = r_doc.get("raw_text", "")
                    r_skills[r_id_str] = [s.name for s in candidate_skills]

        return CandidateProfile(
            profile_id=profile_id,
            user_id=user_id,
            full_name=profile.get("full_name", ""),
            headline=profile.get("headline", ""),
            career_summary=profile.get("career_summary", ""),
            location=profile.get("location", ""),
            skills=candidate_skills,
            preferences=prefs,
            total_years_experience=profile.get("total_years_experience"),
            experience_entries=profile.get("experience", []),
            education_entries=profile.get("education", []),
            resume_ids=r_ids,
            resume_texts=r_texts,
            resume_skills=r_skills,
            embedding=profile.get("embedding"),
        )
