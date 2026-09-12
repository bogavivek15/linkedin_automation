from uuid import uuid4

import pytest
from apps.api.app.domain.job.models import CanonicalJob
from apps.api.app.main import app
from apps.api.app.repositories.job_repository import JobRepository
from apps.api.app.repositories.trust_repository import TrustRepository
from httpx import ASGITransport, AsyncClient


@pytest.fixture(autouse=True)
def reset_stores():
    JobRepository.reset_store()
    TrustRepository.reset_store()
    yield
    JobRepository.reset_store()
    TrustRepository.reset_store()


@pytest.fixture
def test_job() -> CanonicalJob:
    return CanonicalJob(
        id=uuid4(),
        external_id="ext-trust-1",
        source="HIMALAYAS",
        source_url="https://himalayas.app/jobs/trust-test",
        title="Senior Security Engineer",
        normalized_title="senior security engineer",
        company_name="TrustWorks Inc",
        normalized_company="trustworks inc",
        description="Build secure authentication systems and conduct threat modeling. Requires 5 years experience.",
        description_hash="hash-sec-1",
        application_url="https://trustworks.io/careers/apply",
    )


@pytest.mark.asyncio
async def test_assess_trust_and_caching(test_job: CanonicalJob):
    user_id = str(uuid4())
    headers = {"x-user-id": user_id, "x-user-role": "authenticated"}

    # Pre-save job to repository
    await JobRepository.save_job(test_job)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. First assessment request
        res1 = await client.post(
            "/api/v1/trust/assess",
            json={"job_id": str(test_job.id), "force_refresh": False},
            headers=headers,
        )
        assert res1.status_code == 200
        data1 = res1.json()
        assert data1["success"] is True
        assessment1 = data1["data"]
        assert assessment1["job_id"] == str(test_job.id)
        assert "trust_score" in assessment1
        assert "risk_score" in assessment1
        assert "risk_level" in assessment1
        assert "confidence" in assessment1
        assert "evidence" in assessment1
        assert len(assessment1["evidence"]) > 0

        # 2. Get endpoint retrieves cached assessment
        res2 = await client.get(
            f"/api/v1/jobs/{test_job.id}/trust",
            headers=headers,
        )
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["success"] is True
        assert data2["data"]["trust_score"] == assessment1["trust_score"]
        assert data2["data"]["risk_level"] == assessment1["risk_level"]

        # 3. Force refresh works
        res3 = await client.post(
            "/api/v1/trust/assess",
            json={"job_id": str(test_job.id), "force_refresh": True},
            headers=headers,
        )
        assert res3.status_code == 200
        assert res3.json()["success"] is True


@pytest.mark.asyncio
async def test_assess_trust_high_risk_job():
    user_id = str(uuid4())
    headers = {"x-user-id": user_id, "x-user-role": "authenticated"}

    scam_job = CanonicalJob(
        id=uuid4(),
        external_id="ext-scam-1",
        source="JOBICY",
        source_url="https://jobicy.com/jobs/scam",
        title="Data Entry Assistant",
        normalized_title="data entry assistant",
        company_name="QuickCash Ltd",
        normalized_company="quickcash ltd",
        description="Earn $8000/week working from home. A mandatory training fee of $100 is required upon acceptance.",
        description_hash="hash-scam-1",
        application_url="http://sketchy-link.xyz/apply",
    )
    await JobRepository.save_job(scam_job)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get(
            f"/api/v1/jobs/{scam_job.id}/trust",
            headers=headers,
        )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assessment = data["data"]

        # Scam job should be classified HIGH risk with low trust score
        assert assessment["risk_level"] == "HIGH"
        assert assessment["trust_score"] <= 20.0
        assert assessment["risk_score"] >= 90.0
        assert any("fee" in sig.lower() for sig in assessment["suspicious_signals"])


@pytest.mark.asyncio
async def test_trust_endpoint_job_not_found():
    user_id = str(uuid4())
    headers = {"x-user-id": user_id, "x-user-role": "authenticated"}
    missing_id = uuid4()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get(
            f"/api/v1/jobs/{missing_id}/trust",
            headers=headers,
        )
        assert res.status_code == 404
        data = res.json()
        assert data["error"]["code"] == "JOB_NOT_FOUND"


@pytest.mark.asyncio
async def test_trust_user_isolation_private_job():
    owner_id = uuid4()
    other_user_id = uuid4()

    # User A creates a private job
    private_job = CanonicalJob(
        id=uuid4(),
        external_id="ext-priv-1",
        source="MANUAL_IMPORT",
        source_url="https://private-corp.internal/job/1",
        title="Confidential Lead",
        normalized_title="confidential lead",
        company_name="Stealth Co",
        normalized_company="stealth co",
        description="Confidential project details.",
        description_hash="hash-priv-1",
        imported_by_user_id=owner_id,
    )
    await JobRepository.save_job(private_job)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Owner can access and assess
        owner_res = await client.get(
            f"/api/v1/jobs/{private_job.id}/trust",
            headers={"x-user-id": str(owner_id), "x-user-role": "authenticated"},
        )
        assert owner_res.status_code == 200
        assert owner_res.json()["success"] is True

        # 2. Other user is rejected with 404 (user isolation)
        intruder_res = await client.get(
            f"/api/v1/jobs/{private_job.id}/trust",
            headers={"x-user-id": str(other_user_id), "x-user-role": "authenticated"},
        )
        assert intruder_res.status_code == 404
        assert intruder_res.json()["error"]["code"] == "JOB_NOT_FOUND"
