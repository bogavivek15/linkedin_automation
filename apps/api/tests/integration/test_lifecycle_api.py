"""
CareerOS Phase 12 — Application Lifecycle REST API Integration Tests.

Tests endpoints:
POST /api/v1/lifecycle/initialize
GET  /api/v1/lifecycle/{lifecycle_id}
GET  /api/v1/applications/{application_id}/lifecycle
GET  /api/v1/applications/{application_id}/timeline
POST /api/v1/lifecycle/{lifecycle_id}/transition
GET  /api/v1/lifecycle/{lifecycle_id}/follow-ups
POST /api/v1/lifecycle/{lifecycle_id}/follow-ups/{follow_up_id}/status
"""

from uuid import uuid4

import pytest
from apps.api.app.domain.job.models import CanonicalJob
from apps.api.app.main import app
from apps.api.app.repositories.job_repository import JobRepository
from apps.api.app.repositories.lifecycle_repository import LifecycleRepository
from httpx import ASGITransport, AsyncClient


@pytest.fixture(autouse=True)
def reset_stores():
    LifecycleRepository.reset_store()
    JobRepository.reset_store()


@pytest.mark.asyncio
async def test_lifecycle_api_full_workflow():
    user_id = uuid4()
    job_id = uuid4()
    app_id = uuid4()

    # 1. Seed job
    job = CanonicalJob(
        id=job_id,
        source="greenhouse",
        source_url="https://company.com/apply",
        external_id="gh-303",
        title="ML Engineer",
        normalized_title="ml engineer",
        company_name="DeepAI",
        normalized_company="deepai",
        description="Machine learning pipeline engineering",
        description_hash="hash_303",
        application_url="https://company.com/apply",
        status="ACTIVE",
    )
    await JobRepository.save_job(job)

    headers = {"Authorization": f"Bearer {user_id}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 2. Initialize lifecycle
        res_init = await ac.post(
            "/api/v1/lifecycle/initialize",
            headers=headers,
            json={
                "application_id": str(app_id),
                "job_id": str(job_id),
                "initial_status": "SUBMITTED",
            },
        )
        assert res_init.status_code == 200
        lic_data = res_init.json()["data"]
        lic_id = lic_data["id"]
        assert lic_data["current_status"] == "SUBMITTED"

        # 3. GET /api/v1/applications/{application_id}/timeline
        res_tl = await ac.get(f"/api/v1/applications/{app_id}/timeline", headers=headers)
        assert res_tl.status_code == 200
        tl_data = res_tl.json()["data"]
        assert tl_data["current_status"] == "SUBMITTED"
        assert len(tl_data["transitions"]) >= 1

        # 4. POST /api/v1/lifecycle/{lifecycle_id}/transition -> ACKNOWLEDGED
        res_trans = await ac.post(
            f"/api/v1/lifecycle/{lic_id}/transition",
            headers=headers,
            json={
                "to_status": "ACKNOWLEDGED",
                "evidence_type": "RECRUITER_COMMUNICATION",
                "notes": "Received email acknowledgement from recruitment team",
            },
        )
        assert res_trans.status_code == 200
        updated_data = res_trans.json()["data"]["lifecycle"]
        assert updated_data["current_status"] == "ACKNOWLEDGED"

        # 5. POST /api/v1/lifecycle/{lifecycle_id}/transition -> SCREENING
        res_screen = await ac.post(
            f"/api/v1/lifecycle/{lic_id}/transition",
            headers=headers,
            json={
                "to_status": "SCREENING",
                "evidence_type": "RECRUITER_COMMUNICATION",
                "notes": "Recruiter scheduled initial 15-minute screen",
            },
        )
        assert res_screen.status_code == 200
        assert res_screen.json()["data"]["lifecycle"]["current_status"] == "SCREENING"

        # 6. POST /api/v1/lifecycle/{lifecycle_id}/transition -> INTERVIEW
        res_int = await ac.post(
            f"/api/v1/lifecycle/{lic_id}/transition",
            headers=headers,
            json={
                "to_status": "INTERVIEW",
                "evidence_type": "RECRUITER_COMMUNICATION",
                "notes": "Invitation to technical round 1",
            },
        )
        assert res_int.status_code == 200
        assert res_int.json()["data"]["lifecycle"]["current_status"] == "INTERVIEW"

        # 7. Check follow-ups (post-interview thank you generated automatically)
        res_fu_list = await ac.get(
            f"/api/v1/lifecycle/{lic_id}/follow-ups",
            headers=headers,
        )
        assert res_fu_list.status_code == 200
        fu_items = res_fu_list.json()["data"]
        assert len(fu_items) >= 1
        fu_data = fu_items[0]
        assert fu_data["trigger_type"] == "POST_INTERVIEW_THANK_YOU"
        fu_id = fu_data["id"]

        # 8. Update follow-up status to APPROVED
        res_fu_stat = await ac.post(
            f"/api/v1/lifecycle/{lic_id}/follow-ups/{fu_id}/status",
            headers=headers,
            json={"status": "APPROVED", "user_notes": "Looks great, ready to send"},
        )
        assert res_fu_stat.status_code == 200
        assert res_fu_stat.json()["data"]["status"] == "APPROVED"

        # 9. Cross-user isolation
        other_headers = {"Authorization": f"Bearer {uuid4()}"}
        res_iso = await ac.get(f"/api/v1/lifecycle/{lic_id}", headers=other_headers)
        assert res_iso.status_code == 404
