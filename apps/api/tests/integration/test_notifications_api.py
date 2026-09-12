"""
CareerOS Phase 18 — Notifications & Background Automation REST API Integration Tests.
"""

from uuid import uuid4

import pytest
from apps.api.app.main import app
from apps.api.app.repositories.notification_repository import NotificationRepository
from httpx import ASGITransport, AsyncClient


@pytest.fixture(autouse=True)
def reset_notif_store():
    NotificationRepository.reset_store()


@pytest.mark.asyncio
async def test_notifications_api_full_flow():
    user_id = uuid4()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {user_id}"}

        # 1. Trigger background daily pipeline cron
        cron_resp = await client.post("/api/v1/notifications/cron/daily", headers=headers)
        assert cron_resp.status_code == 200
        data = cron_resp.json()["data"]
        assert data["job_name"] == "daily_pipeline_cron"

        # 2. Query notifications
        list_resp = await client.get("/api/v1/notifications", headers=headers)
        assert list_resp.status_code == 200
        notifs = list_resp.json()["data"]
        assert len(notifs) >= 1
        notif_id = notifs[0]["id"]
        assert notifs[0]["read"] is False

        # 3. Mark single notification read
        read_resp = await client.post(f"/api/v1/notifications/{notif_id}/read", headers=headers)
        assert read_resp.status_code == 200
        assert read_resp.json()["data"]["read"] is True

        # 4. Trigger followup cron
        followup_resp = await client.post("/api/v1/notifications/cron/followup", headers=headers)
        assert followup_resp.status_code == 200

        # 5. Mark all read
        all_read_resp = await client.post("/api/v1/notifications/read-all", headers=headers)
        assert all_read_resp.status_code == 200


@pytest.mark.asyncio
async def test_notifications_api_multi_tenant_isolation():
    user_a = uuid4()
    user_b = uuid4()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # User A gets a notification via cron
        await client.post(
            "/api/v1/notifications/cron/daily",
            headers={"Authorization": f"Bearer {user_a}"},
        )

        # User B queries notifications
        resp_b = await client.get(
            "/api/v1/notifications",
            headers={"Authorization": f"Bearer {user_b}"},
        )
        assert resp_b.status_code == 200
        assert len(resp_b.json()["data"]) == 0
