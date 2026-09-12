import logging
from typing import Any
from uuid import UUID

from apps.api.app.core.config import settings
from apps.api.app.domain.job.models import (
    CanonicalJob,
    IngestionStatus,
    JobIngestionRun,
    RawJobPayload,
)
from apps.api.app.repositories.job_repository import JobRepository
from apps.api.app.services.embedding.service import EmbeddingService
from apps.api.app.services.jobs.deduplication import compute_description_hash
from apps.api.app.services.jobs.extraction import extract_requirements
from apps.api.app.services.jobs.normalization import (
    clean_description,
    normalize_company,
    normalize_datetime,
    normalize_employment_type,
    normalize_location,
    normalize_salary,
    normalize_title,
    normalize_work_mode,
)
from apps.api.app.services.jobs.providers.base import JobProvider
from apps.api.app.services.jobs.providers.himalayas import HimalayasProvider
from apps.api.app.services.jobs.providers.jobicy import JobicyProvider
from apps.api.app.services.jobs.providers.mock import (
    MockHimalayasProvider,
    MockJobicyProvider,
)
from apps.api.app.services.jobs.providers.user_url import UserUrlJobImporter

logger = logging.getLogger("careeros.jobs.ingestion")


class JobIngestionService:
    """
    Core Domain Service for job discovery, normalization, deduplication,
    provenance tracking, and optional semantic embedding.
    """

    @classmethod
    def get_providers(cls, provider_names: list[str] | None = None) -> list[JobProvider]:
        """
        Factory to return requested providers with mock fallback for tests/demo.
        """
        requested = [p.upper() for p in (provider_names or ["HIMALAYAS", "JOBICY"])]
        use_mocks = settings.app_env == "test" or settings.demo_mode

        providers: list[JobProvider] = []
        if "HIMALAYAS" in requested:
            providers.append(MockHimalayasProvider() if use_mocks else HimalayasProvider())
        if "JOBICY" in requested:
            providers.append(MockJobicyProvider() if use_mocks else JobicyProvider())

        return providers

    @classmethod
    def normalize_payload(
        cls,
        payload: RawJobPayload,
        imported_by_user_id: UUID | None = None,
    ) -> CanonicalJob:
        """
        Convert untrusted RawJobPayload into CanonicalJob.
        """
        raw = payload.raw_data

        # 1. Extract raw field variations across providers
        raw_title = str(raw.get("title") or raw.get("jobTitle") or "").strip()
        raw_company = str(raw.get("companyName") or raw.get("company") or "").strip()
        raw_desc = str(raw.get("description") or raw.get("jobDescription") or "").strip()
        raw_location = raw.get("locationRestrictions") or raw.get("jobGeo") or raw.get("location")
        raw_work_mode = raw.get("workMode") or raw.get("work_mode")
        raw_emp_type = raw.get("employmentType") or raw.get("jobType")
        raw_app_url = str(
            raw.get("applicationLink")
            or raw.get("url")
            or raw.get("apply_url")
            or payload.source_url
        ).strip()

        # 2. Deterministic normalization
        cleaned_title, norm_title = normalize_title(raw_title)
        cleaned_company, norm_company = normalize_company(raw_company)
        cleaned_desc = clean_description(raw_desc)
        desc_hash = compute_description_hash(cleaned_desc)
        norm_location = normalize_location(raw_location)
        norm_work_mode = normalize_work_mode(raw_work_mode, norm_location)
        norm_emp_type = normalize_employment_type(raw_emp_type)

        # 3. Salary normalization
        s_min = raw.get("minSalary") or raw.get("salaryMin")
        s_max = raw.get("maxSalary") or raw.get("salaryMax")
        s_curr = raw.get("currency") or raw.get("salaryCurrency")
        s_period = raw.get("salaryPeriod")
        salary_min, salary_max, salary_curr = normalize_salary(s_min, s_max, s_curr, s_period)

        # 4. Dates
        posted_at = normalize_datetime(raw.get("pubDate") or raw.get("datePosted"))
        expires_at = normalize_datetime(raw.get("expiryDate") or raw.get("validThrough"))

        # 5. Extract requirements & skills
        req_skills, pref_skills, exp_min = extract_requirements(cleaned_desc)

        return CanonicalJob(
            external_id=payload.external_id,
            source=payload.source.upper(),
            source_url=payload.source_url,
            title=cleaned_title,
            normalized_title=norm_title,
            company_name=cleaned_company,
            normalized_company=norm_company,
            description=cleaned_desc,
            description_hash=desc_hash,
            location=norm_location,
            work_mode=norm_work_mode,
            employment_type=norm_emp_type,
            salary_min=salary_min,
            salary_max=salary_max,
            salary_currency=salary_curr,
            application_url=raw_app_url,
            posted_at=posted_at,
            expires_at=expires_at,
            required_skills=req_skills,
            preferred_skills=pref_skills,
            experience_min=exp_min,
            ingestion_status=IngestionStatus.NORMALIZED,
            metadata={"raw_payload": raw},
            imported_by_user_id=imported_by_user_id,
        )

    @classmethod
    async def process_and_persist_payload(
        cls,
        payload: RawJobPayload,
        imported_by_user_id: UUID | None = None,
        generate_embedding: bool = True,
    ) -> tuple[CanonicalJob, bool]:
        """
        Normalizes payload, performs deduplication, optionally embeds, and persists.
        Returns: (CanonicalJob, is_duplicate)
        """
        canonical = cls.normalize_payload(payload, imported_by_user_id=imported_by_user_id)

        # 1. Deduplication check
        existing = await JobRepository.find_duplicate(
            source=canonical.source,
            external_id=canonical.external_id,
            application_url=canonical.application_url,
            normalized_company=canonical.normalized_company,
            normalized_title=canonical.normalized_title,
            description_hash=canonical.description_hash,
        )

        if existing:
            # Multi-source provenance retention
            await JobRepository.add_source_to_job(
                job_id=existing.id,
                source=canonical.source,
                external_id=canonical.external_id,
                source_url=canonical.source_url,
                raw_payload=payload.raw_data,
            )
            # Re-fetch updated job with new sources
            updated = await JobRepository.get_job_by_id(existing.id, imported_by_user_id)
            return (updated or existing), True

        # 2. Optional Semantic Embedding (Phase 5 integration)
        if generate_embedding and canonical.description:
            try:
                sem_text = EmbeddingService.build_job_semantic_text(
                    title=canonical.title,
                    company=canonical.company_name,
                    description=canonical.description[:1000],
                    requirements=[f"{canonical.experience_min or ''} years experience"] if canonical.experience_min else None,
                    skills=canonical.required_skills,
                )
                vector, _ = await EmbeddingService.embed_text(sem_text)
                canonical.embedding = vector
            except Exception as e:
                logger.warning("Optional job embedding generation skipped: %s", str(e))

        # 3. Persist new canonical job
        saved = await JobRepository.save_job(canonical)
        return saved, False

    @classmethod
    async def run_discovery(
        cls,
        provider_names: list[str] | None = None,
        query: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """
        Execute discovery across providers with failure isolation and run tracking.
        """
        providers = cls.get_providers(provider_names)
        results: list[CanonicalJob] = []
        provider_summaries: dict[str, Any] = {}

        total_fetched = 0
        total_normalized = 0
        total_deduped = 0
        total_failed = 0

        for provider in providers:
            run: JobIngestionRun = await JobRepository.create_ingestion_run(provider.name)
            p_fetched = 0
            p_normalized = 0
            p_deduped = 0
            p_failed = 0
            error_msg: str | None = None

            try:
                payloads = await provider.fetch_jobs(limit=limit, query=query)
                p_fetched = len(payloads)

                for p in payloads:
                    try:
                        job, is_dup = await cls.process_and_persist_payload(p)
                        if is_dup:
                            p_deduped += 1
                        else:
                            p_normalized += 1
                        results.append(job)
                    except Exception as ex:
                        p_failed += 1
                        logger.error("Failed processing payload %s: %s", p.external_id, str(ex))

                status = "COMPLETED" if p_failed == 0 else "PARTIAL"

            except Exception as e:
                status = "FAILED"
                error_msg = str(e)
                p_failed += 1
                logger.error("Provider %s discovery failed: %s", provider.name, error_msg)

            await JobRepository.update_ingestion_run(
                run.id,
                status=status,
                fetched_count=p_fetched,
                normalized_count=p_normalized,
                deduplicated_count=p_deduped,
                failed_count=p_failed,
                error_summary=error_msg,
            )

            provider_summaries[provider.name] = {
                "status": status,
                "fetched": p_fetched,
                "normalized": p_normalized,
                "deduplicated": p_deduped,
                "failed": p_failed,
                "error": error_msg,
            }

            total_fetched += p_fetched
            total_normalized += p_normalized
            total_deduped += p_deduped
            total_failed += p_failed

        return {
            "total_jobs": len(results),
            "total_fetched": total_fetched,
            "total_normalized": total_normalized,
            "total_deduplicated": total_deduped,
            "total_failed": total_failed,
            "providers": provider_summaries,
            "jobs": results,
        }

    @classmethod
    async def import_user_url(cls, url: str, user_id: UUID) -> tuple[CanonicalJob, bool]:
        """
        Safely import public job from user-supplied URL.
        """
        importer = UserUrlJobImporter()
        payload = await importer.import_url(url)
        return await cls.process_and_persist_payload(
            payload,
            imported_by_user_id=user_id,
            generate_embedding=True,
        )

    @classmethod
    async def check_providers_health(cls) -> dict[str, Any]:
        """
        Evaluate health status, timeout thresholds, and reachability for all registered providers.
        """
        import time
        from datetime import datetime, timezone

        providers = cls.get_providers()
        health_reports: dict[str, Any] = {}
        all_healthy = True

        for p in providers:
            t0 = time.perf_counter()
            p_status = "HEALTHY"
            err = None
            try:
                # Test fetch with limit 1
                res = await p.fetch_jobs(limit=1)
                latency = round((time.perf_counter() - t0) * 1000, 1)
            except Exception as ex:
                latency = round((time.perf_counter() - t0) * 1000, 1)
                p_status = "DEGRADED"
                err = str(ex)
                all_healthy = False

            health_reports[p.name] = {
                "name": p.name,
                "status": p_status,
                "latency_ms": latency,
                "timeout_seconds": settings.job_provider_timeout_seconds,
                "retry_limit": 3,
                "error": err,
                "last_checked": datetime.now(timezone.utc).isoformat(),
            }

        return {
            "overall_status": "HEALTHY" if all_healthy else "DEGRADED",
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "providers": health_reports,
        }

