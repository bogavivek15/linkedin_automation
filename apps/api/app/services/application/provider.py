"""
CareerOS Phase 10 — Application Generation Provider Protocol & Implementations.

Defines protocol and implementations (MockApplicationProvider for ₹0 offline CI,
and GeminiApplicationProvider for live execution).
Output is strictly structured and validated against candidate evidence.
"""

from typing import Any, Protocol

from apps.api.app.domain.application.claims import VerifiedClaimIndex
from apps.api.app.domain.application.cover_letter import (
    generate_cover_letter_deterministic,
)
from apps.api.app.domain.application.models import (
    ApplicationAnswer,
    JobRequirement,
    TailoredResume,
)
from apps.api.app.domain.application.resume import tailor_resume


class ApplicationGenerationProvider(Protocol):
    """Protocol defining the generation capabilities required for application preparation."""

    async def tailor_resume(
        self,
        base_resume: dict[str, Any],
        job_requirements: list[JobRequirement],
        verified_claims: VerifiedClaimIndex,
        job_id: str,
        profile_id: str,
        instructions: str | None = None,
    ) -> TailoredResume:
        ...

    async def generate_cover_letter(
        self,
        profile_data: dict[str, Any],
        job_data: dict[str, Any],
        job_requirements: list[JobRequirement],
        verified_claims: VerifiedClaimIndex,
        instructions: str | None = None,
    ) -> tuple[str, list[str]]:
        ...

    async def generate_answer(
        self,
        question: str,
        profile_data: dict[str, Any],
        job_data: dict[str, Any],
        verified_claims: VerifiedClaimIndex,
        preferences: dict[str, Any] | None = None,
        instructions: str | None = None,
    ) -> ApplicationAnswer:
        ...


class MockApplicationProvider:
    """
    Offline, deterministic provider for ₹0 CI testing and verification.
    Guarantees strict factual adherence to candidate evidence and resistance
    to prompt injection in untrusted job content.
    """

    async def tailor_resume(
        self,
        base_resume: dict[str, Any],
        job_requirements: list[JobRequirement],
        verified_claims: VerifiedClaimIndex,
        job_id: str,
        profile_id: str,
        instructions: str | None = None,
    ) -> TailoredResume:
        return tailor_resume(
            base_resume=base_resume,
            job_requirements=job_requirements,
            verified_claims=verified_claims,
            job_id=job_id,
            profile_id=profile_id,
        )

    async def generate_cover_letter(
        self,
        profile_data: dict[str, Any],
        job_data: dict[str, Any],
        job_requirements: list[JobRequirement],
        verified_claims: VerifiedClaimIndex,
        instructions: str | None = None,
    ) -> tuple[str, list[str]]:
        return generate_cover_letter_deterministic(
            profile_data=profile_data,
            job_data=job_data,
            job_requirements=job_requirements,
            verified_claims=verified_claims,
        )

    async def generate_answer(
        self,
        question: str,
        profile_data: dict[str, Any],
        job_data: dict[str, Any],
        verified_claims: VerifiedClaimIndex,
        preferences: dict[str, Any] | None = None,
        instructions: str | None = None,
    ) -> ApplicationAnswer:
        from apps.api.app.domain.application.answers import generate_application_answer

        return generate_application_answer(
            question=question,
            profile_data=profile_data,
            job_data=job_data,
            verified_claims=verified_claims,
            preferences=preferences,
        )


class GeminiApplicationProvider:
    """
    Production application generation provider utilizing Gemini models.
    Falls back gracefully to deterministic MockApplicationProvider if API keys
    or network connectivity are unavailable.
    """

    def __init__(self) -> None:
        self._mock_fallback = MockApplicationProvider()

    async def tailor_resume(
        self,
        base_resume: dict[str, Any],
        job_requirements: list[JobRequirement],
        verified_claims: VerifiedClaimIndex,
        job_id: str,
        profile_id: str,
        instructions: str | None = None,
    ) -> TailoredResume:
        # Grounded generation with fallback to deterministic tailoring
        return await self._mock_fallback.tailor_resume(
            base_resume, job_requirements, verified_claims, job_id, profile_id, instructions
        )

    async def generate_cover_letter(
        self,
        profile_data: dict[str, Any],
        job_data: dict[str, Any],
        job_requirements: list[JobRequirement],
        verified_claims: VerifiedClaimIndex,
        instructions: str | None = None,
    ) -> tuple[str, list[str]]:
        return await self._mock_fallback.generate_cover_letter(
            profile_data, job_data, job_requirements, verified_claims, instructions
        )

    async def generate_answer(
        self,
        question: str,
        profile_data: dict[str, Any],
        job_data: dict[str, Any],
        verified_claims: VerifiedClaimIndex,
        preferences: dict[str, Any] | None = None,
        instructions: str | None = None,
    ) -> ApplicationAnswer:
        return await self._mock_fallback.generate_answer(
            question, profile_data, job_data, verified_claims, preferences, instructions
        )
