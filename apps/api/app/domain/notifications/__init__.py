"""
CareerOS Phase 18 — Notifications Domain Package.
"""

from apps.api.app.domain.notifications.models import (
    NotificationRecord,
    NotificationSeverity,
    NotificationType,
)
from apps.api.app.domain.notifications.policy import (
    NotificationCooldownViolationError,
    NotificationPolicy,
)

__all__ = [
    "NotificationCooldownViolationError",
    "NotificationPolicy",
    "NotificationRecord",
    "NotificationSeverity",
    "NotificationType",
]
