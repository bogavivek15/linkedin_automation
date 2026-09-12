"""
CareerOS Phase 18 — Anti-Spam & Notification Delivery Policy.

Enforces:
1. Anti-spam deduplication and cooldown windows.
2. Severity tiering.
3. User focus preservation.
"""

from datetime import datetime, timezone

from apps.api.app.core.errors import CareerOSError
from apps.api.app.domain.notifications.models import (
    NotificationSeverity,
    NotificationType,
)


class NotificationCooldownViolationError(CareerOSError):
    """Raised when an automated job attempts to spam a candidate within cooldown window."""

    def __init__(self, key: str):
        super().__init__(
            code="NOTIFICATION_COOLDOWN_ACTIVE",
            message=f"Notification suppressed by anti-spam cooldown for key: {key}",
            status_code=429,
        )


class NotificationPolicy:
    """
    Rules for anti-spam filtering and severity validation.
    """

    DEFAULT_COOLDOWN_SECONDS: int = 3600  # 1 hour

    @classmethod
    def resolve_severity(
        cls,
        notif_type: NotificationType,
        explicit_severity: NotificationSeverity | None = None,
    ) -> NotificationSeverity:
        if explicit_severity:
            return explicit_severity

        if notif_type in ("HIGH_RISK_OPPORTUNITY", "SYSTEM_FAILURE"):
            return "CRITICAL"
        if notif_type in ("APPROVAL_REQUIRED", "INTERVIEW_UPDATE"):
            return "WARNING"
        return "INFO"

    @classmethod
    def is_cooldown_active(
        cls,
        last_sent_at: datetime | None,
        cooldown_seconds: int = DEFAULT_COOLDOWN_SECONDS,
    ) -> bool:
        if not last_sent_at:
            return False
        now = datetime.now(timezone.utc)
        elapsed = (now - last_sent_at).total_seconds()
        return elapsed < cooldown_seconds
