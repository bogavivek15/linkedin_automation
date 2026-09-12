from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

SectionType = Literal[
    "SUMMARY",
    "EXPERIENCE",
    "PROJECTS",
    "EDUCATION",
    "SKILLS",
    "CERTIFICATIONS",
    "ACHIEVEMENTS",
    "PUBLICATIONS",
    "CONTACT",
    "OTHER",
]

ClaimType = Literal[
    "SKILL",
    "METRIC",
    "RESPONSIBILITY",
    "CREDENTIAL",
    "OUTCOME",
]

SourceType = Literal[
    "PROJECT",
    "EXPERIENCE",
    "EDUCATION",
    "CERTIFICATION",
]

VerificationStatus = Literal[
    "VERIFIED",
    "INFERRED",
    "UNCERTAIN",
    "REJECTED",
]

ResumeStatus = Literal[
    "UPLOADED",
    "PROCESSING",
    "PROCESSED",
    "FAILED",
]


class ResumeSection(BaseModel):
    section_type: SectionType
    content: str
    start_offset: int | None = None
    end_offset: int | None = None
    normalized_heading: str | None = None


class ResumeClaim(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    resume_id: UUID
    claim_type: ClaimType
    statement: str
    source_type: SourceType
    source_id: UUID | None = None
    evidence_text: str
    verification_status: VerificationStatus = "UNCERTAIN"
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0)
    allowed_in_tailoring: bool = False


class ResumeChunk(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    resume_id: UUID
    user_id: UUID | None = None
    section_type: SectionType
    content: str
    chunk_index: int
    content_hash: str | None = None
    embedding: list[float] | None = None


class EmbeddingRecord(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID | None = None
    entity_type: str  # 'RESUME_CHUNK', 'PROJECT', 'SKILL', 'PROFILE', 'JOB'
    entity_id: UUID
    source_type: str | None = None
    source_id: UUID | None = None
    model_name: str
    model_version: str = "v1"
    dimensions: int = 768
    content_hash: str
    embedding: list[float]
    created_at: str | None = None


class SemanticSearchResult(BaseModel):
    entity_id: UUID
    entity_type: str
    similarity: float = Field(ge=0.0, le=1.0)
    content: str
    section_type: str | None = None
    source_type: str | None = None
    source_id: UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExtractedResume(BaseModel):
    text: str
    pages: int | None = None
    sections: list[ResumeSection] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ParsedResume(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID | None = None
    file_name: str
    file_size: int
    mime_type: str
    raw_text: str
    status: ResumeStatus = "PROCESSED"
    sections: dict[str, str] = Field(default_factory=dict)
    chunks: list[ResumeChunk] = Field(default_factory=list)
    claims: list[ResumeClaim] = Field(default_factory=list)
