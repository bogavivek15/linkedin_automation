from typing import Any
from uuid import UUID

from apps.api.app.core.security import AuthenticatedUser, get_current_user
from apps.api.app.services.trust.service import TrustAssessmentService
from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="", tags=["Trust & Safety"])


class TrustAssessRequest(BaseModel):
    job_id: UUID
    force_refresh: bool = Field(default=False)


@router.post("/trust/assess")
async def assess_trust(
    req: TrustAssessRequest,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Run or refresh evidence-backed Trust & Safety assessment for a job.
    """
    assessment = await TrustAssessmentService.assess_by_job_id(
        job_id=req.job_id,
        user_id=user.user_id,
        force_refresh=req.force_refresh,
    )
    return {
        "success": True,
        "data": assessment,
        "error": None,
    }


@router.get("/jobs/{job_id}/trust")
async def get_job_trust_assessment(
    job_id: UUID,
    force_refresh: bool = Query(False),
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Get existing trust assessment for an opportunity, generating one if absent.
    """
    assessment = await TrustAssessmentService.assess_by_job_id(
        job_id=job_id,
        user_id=user.user_id,
        force_refresh=force_refresh,
    )
    return {
        "success": True,
        "data": assessment,
        "error": None,
    }
