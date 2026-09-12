"""
CareerOS Phase 9 — Decision API Integration Tests.

Validates the full REST API endpoints:
- POST /api/v1/decisions/evaluate
- GET  /api/v1/jobs/{job_id}/decision
- GET  /api/v1/decisions
- GET  /api/v1/decisions/{decision_id}
- POST /api/v1/decisions/batch
- Enforces user isolation & idempotency
"""

from uuid import uuid4

import pytest
from apps.api.app.domain.job.models import CanonicalJob
from apps.api.app.main import app
from apps.api.app.repositories.job_repository import JobRepository
from apps.api.app.repositories.profile_repository import ProfileRepository
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def sample_job() -> CanonicalJob:
    return CanonicalJob(
        id=uuid4(),
        external_id="ext-dec-1",
        source="HIMALAYAS",
        source_url="https://himalayas.app/jobs/decision-test",
        title="Senior Distributed Systems Engineer",
        normalized_title="senior distributed systems engineer",
        company_name="CloudScale Corp",
        normalized_company="cloudscale corp",
        description="Develop scalable cloud services with Python and Kubernetes. Requires 5 years experience.",
        description_hash="hash-cloudscale-1",
        application_url="https://cloudscale.io/apply",
        is_api_ingested=True,
    )


@pytest.fixture
def sample_job_2() -> CanonicalJob:
    return CanonicalJob(
        id=uuid4(),
        external_id="ext-dec-2",
        source="JOBICY",
        source_url="https://jobicy.com/jobs/decision-test-2",
        title="Backend Developer",
        normalized_title="backend developer",
        company_name="TechStart",
        normalized_company="techstart",
        description="FastAPI microservices developer.",
        description_hash="hash-techstart-2",
        application_url="https://techstart.io/apply",
        is_api_ingested=False,
    )


@pytest.mark.asyncio
async def test_decision_evaluate_endpoint_and_idempotency(sample_job: CanonicalJob):
    """POST /api/v1/decisions/evaluate evaluates and idempotently persists decisions."""
    user_id = uuid4()
    headers = {"x-user-id": str(user_id), "x-user-role": "authenticated"}

    await JobRepository.save_job(sample_job)
    await ProfileRepository.save_profile(
        profile_id=user_id,
        user_id=user_id,
        full_name="Alice Candidate",
        headline="Senior Systems Engineer",
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "job_id": str(sample_job.id),
            "policy": {
                "auto_apply_enabled": True,
                "require_user_approval": False,
            },
            "application_context": {
                "execution_mode": "API",
                "application_url": "https://cloudscale.io/api/apply",
            },
        }

        # 1. First evaluation
        res1 = await client.post("/api/v1/decisions/evaluate", json=payload, headers=headers)
        assert res1.status_code == 200
        data1 = res1.json()
        assert data1["success"] is True
        decision1 = data1["data"]["decision"]
        assert decision1["job_id"] == str(sample_job.id)
        assert "overall_score" in decision1
        assert "action" in decision1
        assert len(decision1["reasons"]) > 0

        # 2. Repeated evaluation for idempotency (same job, same profile)
        res2 = await client.post("/api/v1/decisions/evaluate", json=payload, headers=headers)
        assert res2.status_code == 200
        decision2 = res2.json()["data"]["decision"]
        assert decision2["id"] == decision1["id"]
        assert decision2["action"] == decision1["action"]


@pytest.mark.asyncio
async def test_get_job_decision_and_404(sample_job: CanonicalJob):
    """GET /api/v1/jobs/{job_id}/decision fetches decision or 404."""
    user_id = uuid4()
    headers = {"x-user-id": str(user_id), "x-user-role": "authenticated"}

    await JobRepository.save_job(sample_job)
    await ProfileRepository.save_profile(profile_id=user_id, user_id=user_id)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Before evaluation -> 404
        res_404 = await client.get(f"/api/v1/jobs/{sample_job.id}/decision", headers=headers)
        assert res_404.status_code == 404

        # Evaluate
        eval_res = await client.post(
            "/api/v1/decisions/evaluate",
            json={"job_id": str(sample_job.id)},
            headers=headers,
        )
        assert eval_res.status_code == 200

        # Fetch again -> 200
        res_200 = await client.get(f"/api/v1/jobs/{sample_job.id}/decision", headers=headers)
        assert res_200.status_code == 200
        assert res_200.json()["data"]["decision"]["job_id"] == str(sample_job.id)


@pytest.mark.asyncio
async def test_user_isolation_on_decisions(sample_job: CanonicalJob):
    """User B cannot view or access User A's decisions."""
    user_a = uuid4()
    user_b = uuid4()
    headers_a = {"x-user-id": str(user_a), "x-user-role": "authenticated"}
    headers_b = {"x-user-id": str(user_b), "x-user-role": "authenticated"}

    await JobRepository.save_job(sample_job)
    await ProfileRepository.save_profile(profile_id=user_a, user_id=user_a)
    await ProfileRepository.save_profile(profile_id=user_b, user_id=user_b)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # User A creates decision
        res_a = await client.post(
            "/api/v1/decisions/evaluate",
            json={"job_id": str(sample_job.id)},
            headers=headers_a,
        )
        decision_id = res_a.json()["data"]["decision"]["id"]

        # User B attempts to fetch it directly
        res_b = await client.get(f"/api/v1/decisions/{decision_id}", headers=headers_b)
        assert res_b.status_code == 404

        # User B lists decisions -> should see 0 decisions
        list_b = await client.get("/api/v1/decisions", headers=headers_b)
        assert list_b.status_code == 200
        assert len(list_b.json()["data"]["decisions"]) == 0


@pytest.mark.asyncio
async def test_batch_decisions_endpoint(sample_job: CanonicalJob, sample_job_2: CanonicalJob):
    """POST /api/v1/decisions/batch evaluates multiple jobs."""
    user_id = uuid4()
    headers = {"x-user-id": str(user_id), "x-user-role": "authenticated"}

    await JobRepository.save_job(sample_job)
    await JobRepository.save_job(sample_job_2)
    await ProfileRepository.save_profile(profile_id=user_id, user_id=user_id)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {"job_ids": [str(sample_job.id), str(sample_job_2.id)]}
        res = await client.post("/api/v1/decisions/batch", json=payload, headers=headers)
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["total_evaluated"] == 2
        assert len(data["decisions"]) == 2
