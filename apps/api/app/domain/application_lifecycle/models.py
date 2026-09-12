"""
CareerOS Phase 12 — Application Lifecycle & Communication Intelligence Domain Models.

Strongly typed models for application lifecycle tracking, auditable state transitions,
evidence validation, and human-in-the-loop follow-up recommendations.
"""

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

LifecycleStatus = Literal[
    "DISCOVERED",
    "QUALIFIED",
    "PACKAGE_READY",
    "AWAITING_APPROVAL",
    "PREPARED",
    "REVIEW_REQUIRED",
    "APPROVED",
    "HANDOFF",
    "SUBMITTED",
    "ACKNOWLEDGED",
    "SCREENING",
    "ASSESSMENT",
    "INTERVIEW",
    "TECHNICAL",
    "HR",
    "OFFER",
    "REJECTED",
    "WITHDRAWN",
    "NO_RESPONSE",
    "ARCHIVED",
]

LifecycleEvidenceType = Literal[
    "USER_CONFIRMATION",
    "RECRUITER_COMMUNICATION",
    "PORTAL_STATUS",
    "IMPORTED_EMAIL",
    "API_RESPONSE",
    "MANUALLY_ENTERED",
]

FollowUpStatus = Literal["PENDING", "APPROVED", "DISMISSED", "SENT"]


class StatusTransition(BaseModel):
    """
    Auditable transition between lifecycle states backed by evidence.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    lifecycle_id: str
    user_id: str
    from_status: LifecycleStatus
    to_status: LifecycleStatus
    evidence_type: LifecycleEvidenceType
    evidence_details: dict[str, Any] = Field(default_factory=dict)
    actor: str = "USER"
    notes: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FollowUpRecommendation(BaseModel):
    """
    Recommendation for follow-up communication based on waiting periods or interview stages.
    Must be approved by the candidate before sending.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    lifecycle_id: str
    user_id: str
    trigger_type: str  # e.g. WAITING_PERIOD_ELAPSED, POST_INTERVIEW_THANK_YOU
    status: FollowUpStatus = "PENDING"
    recommended_send_date: datetime
    template_subject: str
    template_body: str
    user_notes: str | None = None
    sent_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class LifecycleRecord(BaseModel):
    """
    Persistent application lifecycle state tracking an opportunity through its entire journey.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    application_id: str
    user_id: str
    job_id: str
    current_status: LifecycleStatus = "PREPARED"
    last_transition_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)
    transitions: list[StatusTransition] = Field(default_factory=list)
    follow_up_recommendations: list[FollowUpRecommendation] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
