from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from apps.api.app.domain.job.models import CanonicalJob, JobProvenanceRecord
from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    UNKNOWN = "UNKNOWN"


class ConfidenceLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class EvidenceSentiment(str, Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"
    UNKNOWN = "UNKNOWN"


class EvidenceSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class EvidenceCategory(str, Enum):
    COMPANY_IDENTITY = "COMPANY_IDENTITY"
    COMPANY_WEBSITE = "COMPANY_WEBSITE"
    DOMAIN = "DOMAIN"
    APPLICATION_DOMAIN = "APPLICATION_DOMAIN"
    JOB_CONSISTENCY = "JOB_CONSISTENCY"
    PUBLIC_REPUTATION = "PUBLIC_REPUTATION"
    PAYMENT_REQUEST = "PAYMENT_REQUEST"
    SENSITIVE_INFORMATION = "SENSITIVE_INFORMATION"
    URGENCY = "URGENCY"
    COMPENSATION = "COMPENSATION"
    IMPERSONATION = "IMPERSONATION"
    CONTACT_INFORMATION = "CONTACT_INFORMATION"
    JOB_DESCRIPTION = "JOB_DESCRIPTION"
    MISSING_INFORMATION = "MISSING_INFORMATION"


class TrustEvidence(BaseModel):
    """
    Structured evidence record supporting a trust assessment.
    Never created without provenance or deterministic origin.
    """

    evidence_type: str  # from EvidenceCategory or extension
    source_name: str
    source_url: str | None = None
    claim: str
    sentiment: EvidenceSentiment = EvidenceSentiment.NEUTRAL
    severity: EvidenceSeverity = EvidenceSeverity.LOW
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TrustAssessment(BaseModel):
    """
    Multi-signal, evidence-backed trust and risk assessment.
    Core Invariant: Trust is an evidence-backed risk assessment,
    not a guarantee that a company or job is legitimate.
    """

    id: UUID = Field(default_factory=uuid4)
    job_id: UUID

    trust_score: float = Field(ge=0.0, le=100.0)
    risk_score: float = Field(ge=0.0, le=100.0)

    risk_level: RiskLevel
    confidence: ConfidenceLevel

    positive_signals: list[str] = Field(default_factory=list)
    suspicious_signals: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)

    evidence: list[TrustEvidence] = Field(default_factory=list)
    explanation: str

    assessment_version: str = "v1"
    assessed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TrustContext(BaseModel):
    """
    Contextual opportunity data passed to evidence collectors.
    """

    job: CanonicalJob
    company_name: str
    company_website: str | None = None
    application_url: str | None = None
    sources: list[JobProvenanceRecord] = Field(default_factory=list)
