"""
Unit tests for CareerOS Phase 18 — Notification Policies & Anti-Spam Controls.
"""

from datetime import datetime, timedelta, timezone

from apps.api.app.domain.notifications.policy import NotificationPolicy


def test_notification_severity_resolution():
    # Critical by default
    assert NotificationPolicy.resolve_severity("HIGH_RISK_OPPORTUNITY") == "CRITICAL"
    assert NotificationPolicy.resolve_severity("SYSTEM_FAILURE") == "CRITICAL"

    # Warning by default
    assert NotificationPolicy.resolve_severity("APPROVAL_REQUIRED") == "WARNING"

    # Info by default
    assert NotificationPolicy.resolve_severity("FOLLOW_UP_RECOMMENDATION") == "INFO"

    # Explicit override honored
    assert (
        NotificationPolicy.resolve_severity("FOLLOW_UP_RECOMMENDATION", explicit_severity="WARNING")
        == "WARNING"
    )


def test_anti_spam_cooldown_active():
    now = datetime.now(timezone.utc)
    recent_time = now - timedelta(minutes=15)
    old_time = now - timedelta(hours=2)

    # 15 minutes ago within 1 hour cooldown is ACTIVE
    assert NotificationPolicy.is_cooldown_active(recent_time, cooldown_seconds=3600) is True

    # 2 hours ago is EXPIRED
    assert NotificationPolicy.is_cooldown_active(old_time, cooldown_seconds=3600) is False

    # None is EXPIRED (never sent)
    assert NotificationPolicy.is_cooldown_active(None, cooldown_seconds=3600) is False
