from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class WorkMode(str, Enum):
    REMOTE = "REMOTE"
    HYBRID = "HYBRID"
    ONSITE = "ONSITE"
    UNKNOWN = "UNKNOWN"


class EmploymentType(str, Enum):
    FULL_TIME = "FULL_TIME"
    PART_TIME = "PART_TIME"
    CONTRACT = "CONTRACT"
    INTERNSHIP = "INTERNSHIP"
    TEMPORARY = "TEMPORARY"
    APPRENTICESHIP = "APPRENTICESHIP"
    UNKNOWN = "UNKNOWN"


class IngestionStatus(str, Enum):
    DISCOVERED = "DISCOVERED"
    NORMALIZED = "NORMALIZED"
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    FAILED = "FAILED"


class RawJobPayload(BaseModel):
    """
    Untrusted external payload from a job provider or user-submitted URL.
    """

    source: str  # 'HIMALAYAS', 'JOBICY', 'USER_SUBMISSION', etc.
    external_id: str
    source_url: str
    raw_data: dict[str, Any]
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class JobProvenanceRecord(BaseModel):
    """
    Provenance tracking for each source where this opportunity was observed.
    """

    id: UUID = Field(default_factory=uuid4)
    job_id: UUID
    source: str
    source_url: str
    external_id: str
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    raw_payload: dict[str, Any] | None = None


class CanonicalJob(BaseModel):
    """
    Canonical, normalized CareerOS job representation.
    No provider-specific fields leak into this model.
    """

    id: UUID = Field(default_factory=uuid4)
    external_id: str
    source: str
    source_url: str

    title: str
    normalized_title: str
    company_name: str
    normalized_company: str

    description: str
    description_hash: str

    location: str | None = None
    work_mode: WorkMode = WorkMode.REMOTE
    employment_type: EmploymentType = EmploymentType.FULL_TIME

    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str = "USD"
    is_paid: bool = True

    application_url: str | None = None

    posted_at: datetime | None = None
    expires_at: datetime | None = None

    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    experience_min: float | None = None

    ingestion_status: IngestionStatus = IngestionStatus.NORMALIZED
    normalization_version: str = "v1"
    is_active: bool = True

    trust_assessment: dict[str, Any] | None = None

    metadata: dict[str, Any] = Field(default_factory=dict)
    embedding: list[float] | None = None
    imported_by_user_id: UUID | None = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    sources: list[JobProvenanceRecord] = Field(default_factory=list)

    @property
    def source_job_id(self) -> str:
        return self.external_id


class JobIngestionRun(BaseModel):
    """
    Audit record for provider ingestion runs.
    """

    id: UUID = Field(default_factory=uuid4)
    provider: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    status: str = "RUNNING"
    fetched_count: int = 0
    normalized_count: int = 0
    deduplicated_count: int = 0
    failed_count: int = 0
    error_summary: str | None = None
