"""
CareerOS Phase 10 — Application Package Repository.

In-memory transactional store for prepared application packages.
Enforces strict user isolation and idempotency matching 023_application_packages.sql.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from apps.api.app.domain.application.models import ApplicationPackage


class ApplicationRepository:
    """
    Repository for persisting and querying ApplicationPackage records.
    Provides user isolation and idempotency per (user_id, job_id, package_version).
    """

    _packages: dict[str, dict[str, Any]] = {}  # package_id -> dict
    _index_user_job_version: dict[str, str] = {}  # f"{user_id}:{job_id}:{version}" -> package_id

    @classmethod
    def reset_store(cls) -> None:
        """Helper for test isolation."""
        cls._packages.clear()
        cls._index_user_job_version.clear()

    @classmethod
    async def save_package(
        cls,
        package: ApplicationPackage,
        user_id: UUID,
    ) -> ApplicationPackage:
        """
        Save or upsert an ApplicationPackage.
        Upserts on (user_id, job_id, package_version) for idempotency.
        """
        composite_key = f"{user_id}:{package.job_id}:{package.package_version}"
        existing_id = cls._index_user_job_version.get(composite_key)

        if existing_id:
            package = package.model_copy(update={"id": existing_id, "updated_at": datetime.now(timezone.utc)})
            pkg_id = existing_id
        else:
            pkg_id = str(package.id)

        doc = {
            "id": pkg_id,
            "profile_id": str(package.profile_id),
            "job_id": str(package.job_id),
            "decision_id": str(package.decision_id) if package.decision_id else None,
            "user_id": str(user_id),
            "resume_id": str(package.resume_id) if package.resume_id else None,
            "tailored_resume_id": str(package.tailored_resume_id) if package.tailored_resume_id else None,
            "cover_letter": package.cover_letter,
            "application_answers": [a.model_dump(mode="json") for a in package.application_answers],
            "selected_skills": package.selected_skills,
            "supporting_claim_ids": package.supporting_claim_ids,
            "validation_status": package.validation_status,
            "quality_status": package.quality_status,
            "quality": package.quality.model_dump(mode="json") if package.quality else None,
            "warnings": package.warnings,
            "blocking_issues": package.blocking_issues,
            "package_version": package.package_version,
            "created_at": package.created_at,
            "updated_at": package.updated_at,
            "_raw_model": package,
        }

        cls._packages[pkg_id] = doc
        cls._index_user_job_version[composite_key] = pkg_id
        return package

    @classmethod
    async def get_package(
        cls,
        package_id: str | UUID,
        user_id: UUID,
    ) -> ApplicationPackage | None:
        """
        Retrieve package by ID enforcing user isolation.
        """
        doc = cls._packages.get(str(package_id))
        if not doc or doc.get("user_id") != str(user_id):
            return None
        return doc.get("_raw_model")

    @classmethod
    async def get_package_for_job(
        cls,
        job_id: str | UUID,
        user_id: UUID,
    ) -> ApplicationPackage | None:
        """
        Retrieve latest package prepared for a specific job under the user's account.
        """
        matching = [
            d["_raw_model"]
            for d in cls._packages.values()
            if d.get("user_id") == str(user_id) and d.get("job_id") == str(job_id)
        ]
        if not matching:
            return None
        matching.sort(key=lambda p: p.created_at, reverse=True)
        return matching[0]

    @classmethod
    async def list_packages_for_user(
        cls,
        user_id: UUID,
        status: str | None = None,
    ) -> list[ApplicationPackage]:
        """
        List all application packages for a user, optionally filtered by validation_status.
        """
        results = [
            d["_raw_model"]
            for d in cls._packages.values()
            if d.get("user_id") == str(user_id)
            and (status is None or d.get("validation_status") == status)
        ]
        results.sort(key=lambda p: p.created_at, reverse=True)
        return results

    @classmethod
    async def list_packages_for_profile(
        cls,
        profile_id: str | UUID,
        user_id: UUID,
    ) -> list[ApplicationPackage]:
        """
        List all application packages for a specific profile.
        """
        results = [
            d["_raw_model"]
            for d in cls._packages.values()
            if d.get("user_id") == str(user_id) and d.get("profile_id") == str(profile_id)
        ]
        results.sort(key=lambda p: p.created_at, reverse=True)
        return results

    @classmethod
    async def update_package_status(
        cls,
        package_id: str | UUID,
        user_id: UUID,
        status: str,
    ) -> ApplicationPackage | None:
        """
        Update package validation status (e.g. APPROVED, REQUIRES_VERIFICATION).
        """
        doc = cls._packages.get(str(package_id))
        if not doc or doc.get("user_id") != str(user_id):
            return None

        pkg: ApplicationPackage = doc["_raw_model"]
        updated_pkg = pkg.model_copy(
            update={
                "validation_status": status,
                "updated_at": datetime.now(timezone.utc),
            }
        )
        doc["validation_status"] = status
        doc["updated_at"] = updated_pkg.updated_at
        doc["_raw_model"] = updated_pkg
        return updated_pkg
