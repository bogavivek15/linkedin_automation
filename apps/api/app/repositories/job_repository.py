from datetime import datetime, timezone
import re
from typing import Any
from uuid import UUID

from apps.api.app.core.database import DatabaseManager
from apps.api.app.core.logging import logger
from apps.api.app.domain.job.models import (
    CanonicalJob,
    EmploymentType,
    JobIngestionRun,
    JobProvenanceRecord,
    WorkMode,
)
from apps.api.app.services.jobs.deduplication import are_jobs_duplicate


class JobRepository:
    """
    Repository for Canonical Jobs, Job Sources (Cross-source Deduplication),
    and Ingestion Audit Runs.
    Adheres strictly to:
    - 005_companies_jobs.sql
    - 013_rls.sql
    - 016_job_ingestion.sql
    Provides an in-memory transactional store for ₹0 test and demo execution.
    """

    # In-memory stores
    _jobs: dict[str, dict[str, Any]] = {}
    _job_sources: dict[str, list[dict[str, Any]]] = {}  # job_id -> list[source_dicts]
    _ingestion_runs: dict[str, dict[str, Any]] = {}

    @classmethod
    def reset_store(cls) -> None:
        """Helper for test isolation."""
        cls._jobs.clear()
        cls._job_sources.clear()
        cls._ingestion_runs.clear()

    @classmethod
    async def find_duplicate(
        cls,
        source: str,
        external_id: str,
        application_url: str | None,
        normalized_company: str,
        normalized_title: str,
        description_hash: str,
    ) -> CanonicalJob | None:
        """
        Check if an existing job matches using multi-signal deduplication.
        """
        for job_data in cls._jobs.values():
            if are_jobs_duplicate(
                job_a_source=job_data["source"],
                job_a_ext_id=job_data["external_id"],
                job_a_url=job_data.get("application_url"),
                job_a_company_norm=job_data.get("normalized_company", ""),
                job_a_title_norm=job_data.get("normalized_title", ""),
                job_a_desc_hash=job_data.get("description_hash", ""),
                job_b_source=source,
                job_b_ext_id=external_id,
                job_b_url=application_url,
                job_b_company_norm=normalized_company,
                job_b_title_norm=normalized_title,
                job_b_desc_hash=description_hash,
            ):
                return cls._dict_to_model(job_data)

            # Also check against associated secondary sources
            sources = cls._job_sources.get(str(job_data["id"]), [])
            for s in sources:
                if s["source"].upper() == source.upper() and s["external_id"] == external_id:
                    return cls._dict_to_model(job_data)

        return None

    @classmethod
    async def save_job(cls, job: CanonicalJob) -> CanonicalJob:
        """
        Save or update a CanonicalJob record and its primary source provenance.
        """
        job_id_str = str(job.id)
        now = datetime.now(timezone.utc).isoformat()

        job_dict = {
            "id": job.id,
            "external_id": job.external_id,
            "source": job.source,
            "source_url": job.source_url,
            "title": job.title,
            "normalized_title": job.normalized_title,
            "company_name": job.company_name,
            "normalized_company": job.normalized_company,
            "description": job.description,
            "description_hash": job.description_hash,
            "location": job.location,
            "work_mode": job.work_mode.value,
            "employment_type": job.employment_type.value,
            "salary_min": job.salary_min,
            "salary_max": job.salary_max,
            "salary_currency": job.salary_currency,
            "application_url": job.application_url,
            "posted_at": job.posted_at.isoformat() if job.posted_at else None,
            "expires_at": job.expires_at.isoformat() if job.expires_at else None,
            "required_skills": job.required_skills,
            "preferred_skills": job.preferred_skills,
            "experience_min": job.experience_min,
            "ingestion_status": job.ingestion_status.value,
            "normalization_version": job.normalization_version,
            "is_active": job.is_active,
            "trust_assessment": job.trust_assessment,
            "metadata": job.metadata,
            "embedding": job.embedding,
            "imported_by_user_id": job.imported_by_user_id,
            "created_at": job.created_at.isoformat() if getattr(job, "created_at", None) else now,
            "updated_at": now,
        }
        cls._jobs[job_id_str] = job_dict

        # Ensure primary source is recorded in sources
        if job_id_str not in cls._job_sources:
            cls._job_sources[job_id_str] = []

        # Check if primary source already present
        existing_src = any(
            s["source"] == job.source and s["external_id"] == job.external_id
            for s in cls._job_sources[job_id_str]
        )
        if not existing_src:
            cls._job_sources[job_id_str].append(
                {
                    "job_id": job.id,
                    "source": job.source,
                    "source_url": job.source_url,
                    "external_id": job.external_id,
                    "retrieved_at": now,
                    "raw_payload": job.metadata.get("raw_payload"),
                }
            )

        return cls._dict_to_model(job_dict)

    @classmethod
    async def add_source_to_job(
        cls,
        job_id: UUID,
        source: str,
        external_id: str,
        source_url: str,
        raw_payload: dict[str, Any] | None = None,
    ) -> None:
        """
        Record an additional provider source for an existing canonical job.
        """
        job_id_str = str(job_id)
        if job_id_str not in cls._job_sources:
            cls._job_sources[job_id_str] = []

        now = datetime.now(timezone.utc).isoformat()
        exists = any(
            s["source"] == source and s["external_id"] == external_id
            for s in cls._job_sources[job_id_str]
        )
        if not exists:
            cls._job_sources[job_id_str].append(
                {
                    "job_id": job_id,
                    "source": source,
                    "source_url": source_url,
                    "external_id": external_id,
                    "retrieved_at": now,
                    "raw_payload": raw_payload,
                }
            )

    @classmethod
    async def get_job_by_id(cls, job_id: UUID, user_id: UUID | None = None) -> CanonicalJob | None:
        """
        Retrieve a single canonical job enforcing user access rules.
        """
        job_dict = cls._jobs.get(str(job_id))

        # Check Supabase if configured and not found in-memory
        if not job_dict and DatabaseManager.is_configured():
            try:
                client = DatabaseManager.get_client()
                res = client.table("jobs").select("*").eq("id", str(job_id)).execute()
                if res.data:
                    job_dict = res.data[0]
            except Exception as e:
                logger.warning(f"Failed to fetch job {job_id} from Supabase: {e}")

        if not job_dict:
            return None

        # RLS Isolation: if private imported job, only the owner can access
        imported_by = job_dict.get("imported_by_user_id")
        if imported_by is not None and str(imported_by) != str(user_id) if user_id else (imported_by is not None):
            return None

        return cls._dict_to_model(job_dict)

    @classmethod
    async def list_jobs(
        cls,
        *,
        query: str | None = None,
        work_mode: str | None = None,
        employment_type: str | None = None,
        source: str | None = None,
        limit: int = 50,
        offset: int = 0,
        user_id: UUID | None = None,
    ) -> tuple[list[CanonicalJob], int]:
        """
        List active jobs filtered by parameters, respecting RLS visibility.
        Fetches from Supabase if configured, falling back to in-memory store.
        """
        raw_jobs: list[dict[str, Any]] = []

        # If in-memory store has jobs (e.g. from active session, unit tests, or recent discovery), use them
        if cls._jobs:
            raw_jobs = list(cls._jobs.values())
        elif DatabaseManager.is_configured():
            try:
                client = DatabaseManager.get_client()
                db_query = client.table("jobs").select("*").eq("is_active", True)

                if work_mode:
                    db_query = db_query.eq("work_mode", work_mode.upper())
                if employment_type:
                    db_query = db_query.eq("employment_type", employment_type.upper())
                if source:
                    db_query = db_query.eq("source", source.upper())

                res = db_query.order("created_at", desc=True).execute()
                if res.data:
                    raw_jobs = res.data
            except Exception as e:
                logger.warning(f"Failed to fetch jobs from Supabase, falling back to memory: {e}")

        results: list[dict[str, Any]] = []

        for job_dict in raw_jobs:
            if not job_dict.get("is_active", True):
                continue

            # RLS filter: public jobs (imported_by_user_id is None) OR user's own imported jobs
            imported_by = job_dict.get("imported_by_user_id")
            if imported_by is not None and (str(imported_by) != str(user_id) if user_id else True):
                continue

            # Memory filters if not applied at DB level
            if work_mode and job_dict.get("work_mode") != work_mode.upper():
                continue
            if employment_type and job_dict.get("employment_type") != employment_type.upper():
                continue
            if source and job_dict.get("source") != source.upper():
                continue
            if query and query.strip():
                q = query.strip().lower()
                q_words = [w for w in re.findall(r"\b\w+\b", q) if len(w) > 0]
                title = (job_dict.get("title") or "").lower()
                company = (job_dict.get("company_name") or "").lower()
                desc = (job_dict.get("description") or "").lower()
                skills = [s.lower() for s in (job_dict.get("required_skills") or [])]
                
                def matches_word(word: str) -> bool:
                    pattern = rf"\b{re.escape(word)}\b"
                    return bool(
                        re.search(pattern, title)
                        or re.search(pattern, company)
                        or re.search(pattern, desc)
                        or any(re.search(pattern, s) for s in skills)
                    )

                # If exact query phrase isn't present, verify all tokens match with word boundaries
                if q not in title and q not in company and q not in desc and not any(q in s for s in skills):
                    if not (q_words and all(matches_word(w) for w in q_words)):
                        continue

            results.append(job_dict)

        # Sort newest first
        results.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
        total = len(results)
        paginated = results[offset : offset + limit]

        return [cls._dict_to_model(d) for d in paginated], total

    @classmethod
    async def create_ingestion_run(cls, provider: str) -> JobIngestionRun:
        run = JobIngestionRun(provider=provider)
        cls._ingestion_runs[str(run.id)] = {
            "id": run.id,
            "provider": provider,
            "started_at": run.started_at.isoformat(),
            "completed_at": None,
            "status": "RUNNING",
            "fetched_count": 0,
            "normalized_count": 0,
            "deduplicated_count": 0,
            "failed_count": 0,
            "error_summary": None,
        }
        return run

    @classmethod
    async def update_ingestion_run(
        cls,
        run_id: UUID,
        *,
        status: str,
        fetched_count: int = 0,
        normalized_count: int = 0,
        deduplicated_count: int = 0,
        failed_count: int = 0,
        error_summary: str | None = None,
    ) -> None:
        run_str = str(run_id)
        if run_str in cls._ingestion_runs:
            cls._ingestion_runs[run_str].update(
                {
                    "status": status,
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "fetched_count": fetched_count,
                    "normalized_count": normalized_count,
                    "deduplicated_count": deduplicated_count,
                    "failed_count": failed_count,
                    "error_summary": error_summary,
                }
            )

    @classmethod
    def _dict_to_model(cls, d: dict[str, Any]) -> CanonicalJob:
        sources_list: list[JobProvenanceRecord] = []
        raw_sources = cls._job_sources.get(str(d["id"]), [])
        for s in raw_sources:
            sources_list.append(
                JobProvenanceRecord(
                    job_id=d["id"],
                    source=s.get("source", "UNKNOWN"),
                    source_url=s.get("source_url", ""),
                    external_id=s.get("external_id", ""),
                    raw_payload=s.get("raw_payload"),
                )
            )

        # Handle posted_at and expires_at parsing safely
        def _parse_dt(val: Any) -> datetime | None:
            if not val:
                return None
            if isinstance(val, datetime):
                return val
            try:
                return datetime.fromisoformat(str(val).replace("Z", "+00:00"))
            except Exception:
                return None

        # Safe enum resolution
        raw_work_mode = str(d.get("work_mode", "REMOTE")).upper()
        try:
            work_mode = WorkMode(raw_work_mode)
        except ValueError:
            work_mode = WorkMode.REMOTE

        raw_emp_type = str(d.get("employment_type", "FULL_TIME")).upper()
        try:
            employment_type = EmploymentType(raw_emp_type)
        except ValueError:
            employment_type = EmploymentType.FULL_TIME

        source_url = d.get("source_url") or d.get("application_url") or ""
        external_id = d.get("external_id") or str(d.get("id"))

        return CanonicalJob(
            id=d["id"],
            external_id=external_id,
            source=d.get("source", "DIRECT"),
            source_url=source_url,
            title=d.get("title", "Untitled Position"),
            normalized_title=d.get("normalized_title") or d.get("title", "").lower().strip(),
            company_name=d.get("company_name", "Unknown Company"),
            normalized_company=d.get("normalized_company") or d.get("company_name", "").lower().strip(),
            description=d.get("description") or "",
            description_hash=d.get("description_hash") or "",
            location=d.get("location"),
            work_mode=work_mode,
            employment_type=employment_type,
            salary_min=d.get("salary_min"),
            salary_max=d.get("salary_max"),
            salary_currency=d.get("salary_currency", "USD"),
            application_url=d.get("application_url"),
            posted_at=_parse_dt(d.get("posted_at")),
            expires_at=_parse_dt(d.get("expires_at")),
            required_skills=d.get("required_skills") or [],
            preferred_skills=d.get("preferred_skills") or [],
            experience_min=d.get("experience_min"),
            ingestion_status=d.get("ingestion_status", "NORMALIZED"),
            normalization_version=d.get("normalization_version", "v1"),
            is_active=d.get("is_active", True),
            trust_assessment=d.get("trust_assessment"),
            metadata=d.get("metadata") or {},
            embedding=d.get("embedding"),
            imported_by_user_id=d.get("imported_by_user_id"),
            sources=sources_list,
        )

    @classmethod
    def is_job_stale(cls, job: CanonicalJob | dict[str, Any], max_age_days: int = 90) -> bool:
        """
        Evaluate whether a job posting is stale based on deadline or age.
        Never hallucinates: if dates are missing, does not arbitrarily mark stale.
        """
        now = datetime.now(timezone.utc)

        expires_at = getattr(job, "expires_at", None) or getattr(job, "deadline", None) if isinstance(job, CanonicalJob) else (job.get("expires_at") or job.get("deadline"))
        if isinstance(expires_at, str):
            try:
                expires_at = datetime.fromisoformat(expires_at)
            except Exception:
                expires_at = None

        if expires_at:
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at < now:
                return True

        posted_at = getattr(job, "posted_at", None) or getattr(job, "created_at", None) if isinstance(job, CanonicalJob) else (job.get("posted_at") or job.get("created_at"))
        if isinstance(posted_at, str):
            try:
                posted_at = datetime.fromisoformat(posted_at)
            except Exception:
                posted_at = None

        if posted_at:
            if posted_at.tzinfo is None:
                posted_at = posted_at.replace(tzinfo=timezone.utc)
            age_days = (now - posted_at).total_seconds() / 86400.0
            if age_days > max_age_days:
                return True

        is_active = getattr(job, "is_active", True) if isinstance(job, CanonicalJob) else job.get("is_active", True)
        if not is_active:
            return True

        status = getattr(job, "ingestion_status", "") if isinstance(job, CanonicalJob) else job.get("ingestion_status", "")
        if str(status).upper() == "EXPIRED":
            return True

        return False

    @classmethod
    async def filter_stale_jobs(
        cls,
        jobs: list[CanonicalJob],
        max_age_days: int = 90,
    ) -> tuple[list[CanonicalJob], list[CanonicalJob]]:
        """
        Partition a job list into (active_jobs, stale_jobs).
        """
        active: list[CanonicalJob] = []
        stale: list[CanonicalJob] = []
        for j in jobs:
            if cls.is_job_stale(j, max_age_days=max_age_days):
                stale.append(j)
            else:
                active.append(j)
        return active, stale

    @classmethod
    async def mark_stale_jobs(cls, max_age_days: int = 90) -> int:
        """
        Mark all stale jobs in store as inactive/expired.
        """
        stale_count = 0
        now = datetime.now(timezone.utc).isoformat()
        for job_data in cls._jobs.values():
            if cls.is_job_stale(job_data, max_age_days=max_age_days):
                if job_data.get("is_active", True):
                    job_data["is_active"] = False
                    job_data["ingestion_status"] = "EXPIRED"
                    job_data["updated_at"] = now
                    stale_count += 1
        return stale_count

    @classmethod
    async def get_active_jobs(cls, limit: int = 50) -> list[CanonicalJob]:
        """
        Retrieve only non-stale, active canonical jobs.
        """
        active: list[CanonicalJob] = []
        for job_data in cls._jobs.values():
            if not cls.is_job_stale(job_data):
                active.append(cls._dict_to_model(job_data))
                if len(active) >= limit:
                    break
        return active
