"""
CareerOS Phase 18 — Notifications Repository.

Persistence layer for candidate notifications and anti-spam cooldown state.
Multi-tenant isolated matching 028_notifications.sql.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from apps.api.app.domain.notifications.models import NotificationRecord


class NotificationRepository:
    """
    Repository for storing and querying notifications with cooldown tracking.
    """

    _notifications: dict[str, dict[str, Any]] = {}
    _cooldowns: dict[str, datetime] = {}  # f"{user_id}:{cooldown_key}" -> datetime

    @classmethod
    def reset_store(cls) -> None:
        """Helper for test isolation."""
        cls._notifications.clear()
        cls._cooldowns.clear()

    @classmethod
    async def save_notification(
        cls,
        notification: NotificationRecord,
        user_id: UUID,
    ) -> NotificationRecord:
        notif_id = str(notification.id)
        user_str = str(user_id)

        doc = {
            "id": notif_id,
            "user_id": user_str,
            "notification_type": notification.notification_type,
            "severity": notification.severity,
            "title": notification.title,
            "message": notification.message,
            "action_url": notification.action_url,
            "read": notification.read,
            "read_at": notification.read_at,
            "cooldown_key": notification.cooldown_key,
            "metadata": notification.metadata,
            "created_at": notification.created_at,
            "_raw_model": notification,
        }

        cls._notifications[notif_id] = doc

        if notification.cooldown_key:
            cooldown_lookup = f"{user_str}:{notification.cooldown_key}"
            cls._cooldowns[cooldown_lookup] = notification.created_at

        return notification

    @classmethod
    async def list_notifications(
        cls,
        user_id: UUID,
        unread_only: bool = False,
        limit: int = 50,
    ) -> list[NotificationRecord]:
        user_str = str(user_id)
        results: list[NotificationRecord] = []
        for doc in cls._notifications.values():
            if doc["user_id"] == user_str:
                if unread_only and doc["read"]:
                    continue
                results.append(doc["_raw_model"])
        return sorted(results, key=lambda x: x.created_at, reverse=True)[:limit]

    @classmethod
    async def mark_as_read(
        cls,
        notification_id: str,
        user_id: UUID,
    ) -> bool:
        doc = cls._notifications.get(str(notification_id))
        if not doc or doc["user_id"] != str(user_id):
            return False
        model: NotificationRecord = doc["_raw_model"]
        model.read = True
        model.read_at = datetime.now(timezone.utc)
        doc["read"] = True
        doc["read_at"] = model.read_at
        return True

    @classmethod
    async def mark_all_read(cls, user_id: UUID) -> int:
        user_str = str(user_id)
        now = datetime.now(timezone.utc)
        count = 0
        for doc in cls._notifications.values():
            if doc["user_id"] == user_str and not doc["read"]:
                model: NotificationRecord = doc["_raw_model"]
                model.read = True
                model.read_at = now
                doc["read"] = True
                doc["read_at"] = now
                count += 1
        return count

    @classmethod
    async def get_last_cooldown_time(
        cls,
        user_id: UUID,
        cooldown_key: str,
    ) -> datetime | None:
        cooldown_lookup = f"{user_id}:{cooldown_key}"
        return cls._cooldowns.get(cooldown_lookup)
