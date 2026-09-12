"""
CareerOS Phase 10 — Tailored Resume Repository.

In-memory transactional store for tailored resume artifacts and change diffs.
Enforces strict user isolation and relationship to base resumes.
"""

from typing import Any
from uuid import UUID

from apps.api.app.domain.application.models import TailoredResume


class TailoredResumeRepository:
    """
    Repository for persisting and querying TailoredResume records.
    """

    _resumes: dict[str, dict[str, Any]] = {}  # tailored_resume_id -> dict

    @classmethod
    def reset_store(cls) -> None:
        """Helper for test isolation."""
        cls._resumes.clear()

    @classmethod
    async def save_tailored_resume(
        cls,
        tailored_resume: TailoredResume,
        user_id: UUID,
    ) -> TailoredResume:
        """
        Save a TailoredResume record.
        """
        rid = str(tailored_resume.id)
        doc = {
            "id": rid,
            "base_resume_id": str(tailored_resume.base_resume_id),
            "profile_id": str(tailored_resume.profile_id),
            "job_id": str(tailored_resume.job_id),
            "user_id": str(user_id),
            "version": tailored_resume.version,
            "content": tailored_resume.content,
            "changes": [c.model_dump(mode="json") for c in tailored_resume.changes],
            "supporting_claim_ids": tailored_resume.supporting_claim_ids,
            "validation_status": tailored_resume.validation_status,
            "created_at": tailored_resume.created_at,
            "_raw_model": tailored_resume,
        }
        cls._resumes[rid] = doc
        return tailored_resume

    @classmethod
    async def get_tailored_resume(
        cls,
        resume_id: str | UUID,
        user_id: UUID,
    ) -> TailoredResume | None:
        """
        Retrieve tailored resume enforcing user isolation.
        """
        doc = cls._resumes.get(str(resume_id))
        if not doc or doc.get("user_id") != str(user_id):
            return None
        return doc.get("_raw_model")

    @classmethod
    async def list_for_base_resume(
        cls,
        base_resume_id: str | UUID,
        user_id: UUID,
    ) -> list[TailoredResume]:
        """
        List all tailored versions derived from a specific base resume.
        """
        results = [
            d["_raw_model"]
            for d in cls._resumes.values()
            if d.get("user_id") == str(user_id) and d.get("base_resume_id") == str(base_resume_id)
        ]
        results.sort(key=lambda r: r.created_at, reverse=True)
        return results
