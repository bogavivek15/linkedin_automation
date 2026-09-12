"""
CareerOS Phase 9.x — Domain Models for Graph Orchestration.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class RunStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class RunStage(str, Enum):
    INIT = "INIT"
    DISCOVERY = "DISCOVERY"
    TRUST = "TRUST"
    MATCH = "MATCH"
    DECISION = "DECISION"
    APPROVAL = "APPROVAL"
    FINALIZE = "FINALIZE"


class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class CareerRun(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    profile_id: UUID
    user_id: UUID
    request_id: str
    graph_name: str = "career_intelligence"
    graph_version: str = "v1"
    status: str = RunStatus.RUNNING.value
    current_stage: str = RunStage.INIT.value
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    state_snapshot: dict[str, Any] | None = None


class AgentEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    run_id: str
    profile_id: str
    user_id: str
    job_id: str | None = None
    event_type: str
    agent_name: str
    stage: str
    status: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


class ApprovalRequest(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    profile_id: UUID
    job_id: UUID
    decision_id: UUID | None = None
    user_id: UUID
    status: str = ApprovalStatus.PENDING.value
    requested_action: str = "REVIEW"
    reason: str
    expires_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: datetime | None = None
    resolved_by: UUID | None = None

    # Contextual fields for UI/client consumption
    job_title: str | None = None
    company_name: str | None = None
    match_score: float | None = None
    trust_score: float | None = None
    risk_level: str | None = None
    decision_reasons: list[str] = Field(default_factory=list)

    # Intelligent Explainability Fields (Section 8)
    action_type: str = "SUBMIT_APPLICATION"
    why_matched: list[str] = Field(default_factory=list)
    resume_changes: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    evidence_citations: list[str] = Field(default_factory=list)


class RunCreateRequest(BaseModel):
    profile_id: UUID
    target_roles: list[str] = Field(default_factory=list)
    query: str | None = None
    limit: int = 10
    provider_names: list[str] | None = None
    request_id: str | None = None


class RunResponse(BaseModel):
    success: bool = True
    data: dict[str, Any]
    meta: dict[str, Any] | None = None
