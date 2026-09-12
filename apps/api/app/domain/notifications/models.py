"""
CareerOS Phase 18 — Notifications Domain Models.

Strongly typed models for candidate notifications, anti-spam metadata, and severity tiers.
"""

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

NotificationType = Literal[
    "APPROVAL_REQUIRED",
    "HIGH_RISK_OPPORTUNITY",
    "APPLICATION_UPDATE",
    "INTERVIEW_UPDATE",
    "FOLLOW_UP_RECOMMENDATION",
    "CONTENT_APPROVAL",
    "SYSTEM_FAILURE",
]

NotificationSeverity = Literal[
    "INFO",
    "WARNING",
    "CRITICAL",
]


class NotificationRecord(BaseModel):
    """
    Candidate notification item with action URL, severity, and read state.
    """

    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    notification_type: NotificationType
    severity: NotificationSeverity = "INFO"
    title: str
    message: str
    action_url: str | None = None
    read: bool = False
    read_at: datetime | None = None
    cooldown_key: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
