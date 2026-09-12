"""
CareerOS Phase 9.x — Runs & Approvals REST API Integration Tests.
"""

from uuid import uuid4

import pytest
from apps.api.app.main import app
from apps.api.app.repositories.approval_repository import ApprovalRepository
from apps.api.app.repositories.event_repository import EventRepository
from apps.api.app.repositories.profile_repository import ProfileRepository
from apps.api.app.repositories.run_repository import RunRepository
from httpx import ASGITransport, AsyncClient


@pytest.fixture(autouse=True)
def reset_all_stores():
    RunRepository.reset_store()
    EventRepository.reset_store()
    ApprovalRepository.reset_store()
    ProfileRepository.reset_store()


@pytest.mark.asyncio
async def test_full_runs_and_approvals_api_lifecycle():
    user_id = uuid4()
    profile_id = uuid4()

    # Seed profile in ProfileRepository
    await ProfileRepository.save_profile(
        profile_id=profile_id,
        user_id=user_id,
        full_name="Alice Candidate",
        headline="AI Engineer",
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        headers = {"X-User-Id": str(user_id)}

        # 1. Start a Run
        payload = {
            "profile_id": str(profile_id),
            "target_roles": ["AI Engineer"],
            "query": "python",
            "limit": 3,
            "request_id": "api-run-req-001",
        }

        resp = await ac.post("/api/v1/runs", json=payload, headers=headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["success"] is True
        run_id = data["data"]["run_id"]
        assert run_id is not None

        # 2. Get Run Status
        get_resp = await ac.get(f"/api/v1/runs/{run_id}", headers=headers)
        assert get_resp.status_code == 200
        run_data = get_resp.json()["data"]
        assert run_data["run_id"] == run_id

        # 3. Get Events
        events_resp = await ac.get(f"/api/v1/runs/{run_id}/events", headers=headers)
        assert events_resp.status_code == 200
        events = events_resp.json()["data"]
        assert len(events) > 0
        event_types = [e["event_type"] for e in events]
        assert "RUN_STARTED" in event_types

        # 4. List Runs
        list_resp = await ac.get("/api/v1/runs", headers=headers)
        assert list_resp.status_code == 200
        runs_list = list_resp.json()["data"]
        assert len(runs_list) >= 1

        # 5. Security: Another user cannot view run or events
        other_headers = {"X-User-Id": str(uuid4())}
        sec_resp = await ac.get(f"/api/v1/runs/{run_id}", headers=other_headers)
        assert sec_resp.status_code == 404

        sec_events = await ac.get(f"/api/v1/runs/{run_id}/events", headers=other_headers)
        assert sec_events.status_code == 404
