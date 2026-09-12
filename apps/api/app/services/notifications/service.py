"""
CareerOS Phase 18 — Notifications Service.

Coordinates notification delivery, anti-spam cooldown enforcement,
and multi-tenant read-status management.
"""

from typing import Any
from uuid import UUID

from apps.api.app.domain.notifications.models import (
    NotificationRecord,
    NotificationSeverity,
    NotificationType,
)
from apps.api.app.domain.notifications.policy import (
    NotificationCooldownViolationError,
    NotificationPolicy,
)
from apps.api.app.repositories.notification_repository import NotificationRepository


class NotificationService:
    """
    Business service for managing candidate notifications.
    """

    async def emit_notification(
        self,
        user_id: UUID,
        notification_type: NotificationType,
        title: str,
        message: str,
        action_url: str | None = None,
        severity: NotificationSeverity | None = None,
        cooldown_key: str | None = None,
        cooldown_seconds: int = NotificationPolicy.DEFAULT_COOLDOWN_SECONDS,
        metadata: dict[str, Any] | None = None,
    ) -> NotificationRecord:
        """
        Emit a notification to the candidate, strictly enforcing anti-spam cooldowns.
        """
        if cooldown_key:
            last_sent = await NotificationRepository.get_last_cooldown_time(user_id, cooldown_key)
            if NotificationPolicy.is_cooldown_active(last_sent, cooldown_seconds):
                raise NotificationCooldownViolationError(cooldown_key)

        resolved_severity = NotificationPolicy.resolve_severity(
            notif_type=notification_type,
            explicit_severity=severity,
        )

        record = NotificationRecord(
            user_id=str(user_id),
            notification_type=notification_type,
            severity=resolved_severity,
            title=title,
            message=message,
            action_url=action_url,
            cooldown_key=cooldown_key,
            metadata=metadata or {},
        )

        return await NotificationRepository.save_notification(record, user_id)

    async def list_notifications(
        self,
        user_id: UUID,
        unread_only: bool = False,
        limit: int = 50,
    ) -> list[NotificationRecord]:
        return await NotificationRepository.list_notifications(user_id, unread_only, limit)

    async def mark_as_read(
        self,
        notification_id: str,
        user_id: UUID,
    ) -> bool:
        return await NotificationRepository.mark_as_read(notification_id, user_id)

    async def mark_all_read(self, user_id: UUID) -> int:
        return await NotificationRepository.mark_all_read(user_id)
