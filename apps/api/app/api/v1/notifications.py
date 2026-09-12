"""
CareerOS Phase 18 — Notifications & Background Automation API.

GET    /api/v1/notifications               - List notifications
POST   /api/v1/notifications/{id}/read     - Mark notification read
POST   /api/v1/notifications/read-all      - Mark all read
POST   /api/v1/notifications/cron/daily    - Trigger background daily pipeline
POST   /api/v1/notifications/cron/followup - Trigger background followup check
"""

from apps.api.app.core.security import AuthenticatedUser, get_current_user
from apps.api.app.services.background.jobs import BackgroundAutomationRunner
from apps.api.app.services.notifications.service import NotificationService
from fastapi import APIRouter, Depends, HTTPException, Query

router = APIRouter(prefix="/notifications", tags=["Notifications & Automation"])

_service = NotificationService()
_cron_runner = BackgroundAutomationRunner()


@router.get("", response_model=dict)
async def list_notifications(
    unread_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    List candidate notifications.
    """
    notifs = await _service.list_notifications(
        user_id=current_user.user_id,
        unread_only=unread_only,
        limit=limit,
    )
    return {"success": True, "data": [n.model_dump(mode="json") for n in notifs]}


@router.post("/{notification_id}/read", response_model=dict)
async def mark_read(
    notification_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Mark a notification as read.
    """
    marked = await _service.mark_as_read(notification_id, current_user.user_id)
    if not marked:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"success": True, "data": {"read": True}}


@router.post("/read-all", response_model=dict)
async def mark_all_read(
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Mark all notifications as read for current user.
    """
    count = await _service.mark_all_read(current_user.user_id)
    return {"success": True, "data": {"marked_count": count}}


@router.post("/cron/daily", response_model=dict)
async def trigger_daily_pipeline(
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Trigger daily pipeline cron run (Cloudflare worker endpoint).
    """
    result = await _cron_runner.run_daily_pipeline(current_user.user_id)
    return {"success": True, "data": result}


@router.post("/cron/followup", response_model=dict)
async def trigger_followup_monitor(
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Trigger application followup check cron run.
    """
    result = await _cron_runner.run_followup_monitor(current_user.user_id)
    return {"success": True, "data": result}
