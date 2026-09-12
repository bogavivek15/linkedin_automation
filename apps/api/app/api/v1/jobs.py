from typing import Any
from uuid import UUID

from apps.api.app.core.errors import CareerOSError
from apps.api.app.core.security import AuthenticatedUser, get_current_user
from apps.api.app.repositories.job_repository import JobRepository
from apps.api.app.services.jobs.service import JobIngestionService
from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/jobs", tags=["Jobs"])


class JobDiscoveryRequest(BaseModel):
    providers: list[str] = Field(default=["HIMALAYAS", "JOBICY"])
    query: str | None = None
    limit: int = Field(default=20, ge=1, le=50)


class JobImportUrlRequest(BaseModel):
    url: str


@router.post("/discover")
async def discover_jobs(
    req: JobDiscoveryRequest,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Run multi-source job discovery across Himalayas and Jobicy with failure isolation.
    """
    summary = await JobIngestionService.run_discovery(
        provider_names=req.providers,
        query=req.query,
        limit=req.limit,
    )
    return {
        "success": True,
        "data": summary,
        "error": None,
    }


@router.post("/import-url")
async def import_job_url(
    req: JobImportUrlRequest,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Safely ingest a public job posting from a user-supplied URL.
    """
    job, is_duplicate = await JobIngestionService.import_user_url(
        url=req.url,
        user_id=user.user_id,
    )
    return {
        "success": True,
        "data": {
            "job": job,
            "is_duplicate": is_duplicate,
        },
        "error": None,
    }


@router.get("")
async def list_jobs(
    query: str | None = Query(None),
    work_mode: str | None = Query(None),
    employment_type: str | None = Query(None),
    source: str | None = Query(None),
    limit: int = Query(100, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """
    List active canonical jobs matching filters, with RLS user isolation.
    """
    jobs, total = await JobRepository.list_jobs(
        query=query,
        work_mode=work_mode,
        employment_type=employment_type,
        source=source,
        limit=limit,
        offset=offset,
        user_id=user.user_id,
    )
    return {
        "success": True,
        "data": {
            "jobs": jobs,
            "total": total,
            "limit": limit,
            "offset": offset,
        },
        "error": None,
    }


@router.get("/providers/health")
async def get_providers_health(
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Get live health status, latency, and timeout configuration for all job providers.
    """
    health_data = await JobIngestionService.check_providers_health()
    return {
        "success": True,
        "data": health_data,
        "error": None,
    }


@router.get("/{job_id}")
async def get_job_detail(
    job_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Get detailed canonical job record by ID.
    """
    job = await JobRepository.get_job_by_id(job_id=job_id, user_id=user.user_id)
    if not job:
        raise CareerOSError(
            code="JOB_NOT_FOUND",
            message=f"Job {job_id} not found or inaccessible",
            status_code=404,
        )

    return {
        "success": True,
        "data": job,
        "error": None,
    }
