import logging
from uuid import UUID

from apps.api.app.core.config import settings
from apps.api.app.domain.job.models import CanonicalJob
from apps.api.app.domain.trust.models import TrustAssessment, TrustContext, TrustEvidence
from apps.api.app.repositories.job_repository import JobRepository
from apps.api.app.repositories.trust_repository import TrustRepository
from apps.api.app.services.trust.policy import TrustPolicyEngine
from apps.api.app.services.trust.providers.base import TrustEvidenceProvider
from apps.api.app.services.trust.providers.deterministic import (
    DeterministicEvidenceProvider,
)
from apps.api.app.services.trust.providers.domain import DomainEvidenceProvider
from apps.api.app.services.trust.providers.mock import MockEvidenceProvider

logger = logging.getLogger("careeros.trust.service")


class TrustAssessmentService:
    """
    Core Domain Service for Trust & Safety evidence collection,
    multi-signal evaluation, risk classification, and assessment caching.
    """

    @classmethod
    def get_evidence_providers(cls) -> list[TrustEvidenceProvider]:
        providers: list[TrustEvidenceProvider] = [
            DeterministicEvidenceProvider(),
            DomainEvidenceProvider(),
        ]

        if settings.app_env == "test" or settings.demo_mode:
            providers.append(MockEvidenceProvider())

        return providers

    @classmethod
    async def assess_job(
        cls,
        job: CanonicalJob,
        force_refresh: bool = False,
    ) -> TrustAssessment:
        """
        Assess or return cached trust assessment for a canonical job opportunity.
        """
        # 1. Check existing cached assessment
        if not force_refresh:
            cached = await TrustRepository.get_by_job_id(job.id)
            if cached:
                return cached

        # 2. Build contextual opportunity payload
        context = TrustContext(
            job=job,
            company_name=job.company_name,
            company_website=job.metadata.get("website_url"),
            application_url=job.application_url or job.source_url,
            sources=job.sources,
        )

        # 3. Collect evidence across providers with failure isolation
        providers = cls.get_evidence_providers()
        all_evidence: list[TrustEvidence] = []

        for provider in providers:
            try:
                ev_list = await provider.collect(context)
                all_evidence.extend(ev_list)
            except Exception as e:
                logger.error("Trust evidence provider %s failed: %s", provider.name, str(e))

        # 4. Evaluate via deterministic policy engine
        assessment = TrustPolicyEngine.evaluate(all_evidence, context)

        # 5. Persist and return
        await TrustRepository.save_assessment(assessment)
        return assessment

    @classmethod
    async def assess_by_job_id(
        cls,
        job_id: UUID,
        user_id: UUID | None = None,
        force_refresh: bool = False,
    ) -> TrustAssessment:
        """
        Assess trust for a job ID enforcing access isolation.
        """
        job = await JobRepository.get_job_by_id(job_id=job_id, user_id=user_id)
        if not job:
            from apps.api.app.core.errors import CareerOSError

            raise CareerOSError(
                code="JOB_NOT_FOUND",
                message=f"Job {job_id} not found or inaccessible",
                status_code=404,
            )

        return await cls.assess_job(job, force_refresh=force_refresh)
