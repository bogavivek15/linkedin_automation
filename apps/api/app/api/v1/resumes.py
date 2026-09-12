import time
from uuid import UUID

from apps.api.app.core.errors import CareerOSError
from apps.api.app.core.logging import logger
from apps.api.app.core.security import AuthenticatedUser, get_current_user
from apps.api.app.domain.resume.models import ParsedResume
from apps.api.app.repositories.resume_repository import ResumeRepository
from apps.api.app.services.resume_service import ResumeService
from fastapi import APIRouter, Depends, File, Request, UploadFile

router = APIRouter(prefix="/resumes", tags=["Resumes & Verifiable Claims"])


@router.post("/upload")
async def upload_resume(
    request: Request,
    file: UploadFile = File(...),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Ingest, validate, extract sections, and extract atomic verifiable claims from a resume.
    Persists resume metadata, chunks, and claims with strict user ownership isolation.
    """
    start_time = time.time()
    request_id = getattr(request.state, "request_id", "req-test")
    file_bytes = await file.read()
    content_type = file.content_type or "application/octet-stream"
    filename = file.filename or "resume.pdf"

    logger.info(
        "Resume upload initiated",
        extra={
            "request_id": request_id,
            "user_id": str(current_user.user_id),
            "operation": "RESUME_UPLOAD_STARTED",
            "file_name": filename,
            "file_size": len(file_bytes),
        },
    )

    try:
        parsed_resume: ParsedResume = await ResumeService.parse_and_process_resume(
            filename=filename,
            content_type=content_type,
            file_bytes=file_bytes,
            user_id=current_user.user_id,
        )

        # Persist resume, chunks, and claims
        await ResumeRepository.save_parsed_resume(parsed_resume, current_user)

        # Populate Career Memory with strict provenance tagging
        try:
            from apps.api.app.services.resume_intelligence import ResumeIntelligenceService
            intel_svc = ResumeIntelligenceService()
            await intel_svc.ingest_resume(
                filename=filename,
                content_type=content_type,
                file_bytes=file_bytes,
                user_id=current_user.user_id,
            )
        except Exception as intel_err:
            logger.warning("Resume intelligence memory ingestion skipped: %s", str(intel_err))

        duration = time.time() - start_time
        verified_claims = [c for c in parsed_resume.claims if c.verification_status == "VERIFIED"]

        logger.info(
            "Resume processing completed successfully",
            extra={
                "request_id": request_id,
                "user_id": str(current_user.user_id),
                "resume_id": str(parsed_resume.id),
                "operation": "RESUME_PROCESSING_COMPLETED",
                "duration_ms": round(duration * 1000, 2),
                "total_claims": len(parsed_resume.claims),
                "verified_claims": len(verified_claims),
                "status": "SUCCESS",
            },
        )

        return {
            "success": True,
            "data": parsed_resume.model_dump(mode="json"),
            "error": None,
            "meta": {
                "request_id": request_id,
                "total_claims": len(parsed_resume.claims),
                "verified_claims": len(verified_claims),
                "total_chunks": len(parsed_resume.chunks),
                "duration_seconds": round(duration, 3),
            },
        }
    except CareerOSError as err:
        logger.warning(
            "Resume upload validation or processing error",
            extra={
                "request_id": request_id,
                "user_id": str(current_user.user_id),
                "operation": "RESUME_PROCESSING_FAILED",
                "error_code": err.code,
                "duration_ms": round((time.time() - start_time) * 1000, 2),
                "status": "FAILED",
            },
        )
        raise
    except Exception as exc:
        logger.error(
            "Unexpected error during resume processing",
            extra={
                "request_id": request_id,
                "user_id": str(current_user.user_id),
                "operation": "RESUME_PROCESSING_FAILED",
                "error_code": "DOCUMENT_PROCESSING_FAILED",
                "duration_ms": round((time.time() - start_time) * 1000, 2),
                "status": "FAILED",
            },
            exc_info=True,
        )
        raise CareerOSError(
            code="DOCUMENT_PROCESSING_FAILED",
            message=f"Document processing failed: {exc!s}",
            status_code=500,
        )


@router.get("/{resume_id}/claims")
async def get_resume_claims(
    resume_id: UUID,
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Retrieve all verifiable claims for a resume.
    Strictly verifies ownership: User A cannot access User B's claims.
    """
    request_id = getattr(request.state, "request_id", "req-test")
    claims = await ResumeRepository.get_claims_by_resume_id(resume_id, current_user)

    verified_count = sum(1 for c in claims if c.verification_status == "VERIFIED")
    inferred_count = sum(1 for c in claims if c.verification_status == "INFERRED")
    uncertain_count = sum(1 for c in claims if c.verification_status == "UNCERTAIN")
    rejected_count = sum(1 for c in claims if c.verification_status == "REJECTED")

    return {
        "success": True,
        "data": [c.model_dump(mode="json") for c in claims],
        "error": None,
        "meta": {
            "request_id": request_id,
            "resume_id": str(resume_id),
            "total_claims": len(claims),
            "verified_count": verified_count,
            "inferred_count": inferred_count,
            "uncertain_count": uncertain_count,
            "rejected_count": rejected_count,
        },
    }


@router.get("/{resume_id}")
async def get_resume_by_id(
    resume_id: UUID,
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Retrieve resume metadata by ID, enforcing user ownership.
    """
    request_id = getattr(request.state, "request_id", "req-test")
    resume = await ResumeRepository.get_resume(resume_id, current_user)
    if not resume:
        raise CareerOSError(
            code="RESUME_NOT_FOUND",
            message=f"Resume with ID '{resume_id}' not found",
            status_code=404,
        )

    # Convert non-serializable fields if needed
    serializable_resume = {k: str(v) if isinstance(v, UUID) else v for k, v in resume.items()}

    return {
        "success": True,
        "data": serializable_resume,
        "error": None,
        "meta": {
            "request_id": request_id,
        },
    }


@router.get("/{resume_id}/embeddings/status")
async def get_resume_embeddings_status(
    resume_id: UUID,
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Retrieve semantic embedding status for a resume's chunks.
    """
    request_id = getattr(request.state, "request_id", "req-test")
    status_data = await ResumeRepository.get_resume_embedding_status(resume_id, current_user)

    return {
        "success": True,
        "data": {
            "resume_id": str(status_data["resume_id"]),
            "file_name": status_data["file_name"],
            "total_chunks": status_data["total_chunks"],
            "embedded_chunks": status_data["embedded_chunks"],
            "model_name": status_data["model_name"],
            "dimensions": status_data["dimensions"],
            "status": status_data["status"],
        },
        "error": None,
        "meta": {
            "request_id": request_id,
        },
    }
