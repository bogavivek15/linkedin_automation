from typing import Any
from uuid import UUID

from apps.api.app.domain.resume.models import ParsedResume, ResumeClaim
from pydantic import BaseModel, Field


class ResumeSummary(BaseModel):
    id: UUID
    user_id: UUID | None
    file_name: str
    file_size: int
    mime_type: str
    status: str
    total_sections: int
    total_chunks: int
    total_claims: int
    verified_claims_count: int


class ResumeUploadResponse(BaseModel):
    success: bool = True
    data: ParsedResume
    error: dict[str, Any] | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class ResumeClaimsResponse(BaseModel):
    success: bool = True
    data: list[ResumeClaim]
    error: dict[str, Any] | None = None
    meta: dict[str, Any] = Field(default_factory=dict)
