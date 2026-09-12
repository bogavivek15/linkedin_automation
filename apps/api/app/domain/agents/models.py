"""
CareerOS Phase 16 — Agent Registry & Autonomous Orchestration Domain Models.

Formal representations for the 8 core autonomous agents, agent runs,
and observable execution telemetry.
"""

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

AgentCategory = Literal[
    "ORCHESTRATION",
    "DISCOVERY",
    "SECURITY",
    "IDENTITY",
    "EXECUTION_PREP",
    "OUTREACH",
    "FEEDBACK",
    "KNOWLEDGE",
]

AgentStatus = Literal[
    "ACTIVE",
    "IDLE",
    "STANDBY",
    "MAINTENANCE",
]

RunStatus = Literal[
    "PENDING",
    "RUNNING",
    "PAUSED_WAITING_APPROVAL",
    "COMPLETED",
    "FAILED",
    "CANCELLED",
]


class AgentRegistryEntry(BaseModel):
    """
    Formal metadata record for an autonomous agent operating within CareerOS.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    agent_name: str
    agent_version: str
    category: AgentCategory
    capabilities: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    status: AgentStatus = "ACTIVE"
    last_run_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ObservableAgentEvent(BaseModel):
    """
    Real observable event emitted during agent orchestration. No fake thinking.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    run_id: str
    agent_name: str
    stage: str
    event_type: str
    description: str
    metrics: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentRunRecord(BaseModel):
    """
    Traceable execution instance of a multi-agent orchestration run.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    request_id: str
    user_id: str
    primary_agent: str
    status: RunStatus = "PENDING"
    duration_ms: int = 0
    inputs_metadata: dict[str, Any] = Field(default_factory=dict)
    outputs_metadata: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    events: list[ObservableAgentEvent] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
