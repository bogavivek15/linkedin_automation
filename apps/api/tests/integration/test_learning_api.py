"""
CareerOS Phase 13 — Career Learning & Feedback Loop REST API Integration Tests.
"""

from uuid import uuid4

import pytest
from apps.api.app.main import app
from apps.api.app.repositories.learning_repository import LearningRepository
from httpx import ASGITransport, AsyncClient


@pytest.fixture(autouse=True)
def reset_learning_store():
    LearningRepository.reset_store()


@pytest.mark.asyncio
async def test_learning_api_record_and_query_flow():
    user_id = uuid4()
    profile_id = uuid4()
    job_id = uuid4()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {user_id}"}

        # 1. Record outcome
        record_resp = await client.post(
            "/api/v1/learning/outcomes",
            headers=headers,
            json={
                "profile_id": str(profile_id),
                "job_id": str(job_id),
                "outcome_type": "INTERVIEW_SCHEDULED",
                "match_score": 92.5,
                "trust_score": 88.0,
                "notes": "Python backend engineer role with FastAPI",
                "extracted_skill_gaps": [],
            },
        )
        assert record_resp.status_code == 200
        data = record_resp.json()["data"]
        assert data["outcome"]["outcome_type"] == "INTERVIEW_SCHEDULED"

        # 2. Query outcomes
        outcomes_resp = await client.get(
            f"/api/v1/learning/outcomes?profile_id={profile_id}",
            headers=headers,
        )
        assert outcomes_resp.status_code == 200
        outcomes = outcomes_resp.json()["data"]
        assert len(outcomes) == 1
        assert outcomes[0]["job_id"] == str(job_id)

        # 3. Query patterns
        patterns_resp = await client.get("/api/v1/learning/patterns", headers=headers)
        assert patterns_resp.status_code == 200

        # 4. Query insights
        insights_resp = await client.get("/api/v1/learning/insights", headers=headers)
        assert insights_resp.status_code == 200

        # 5. Trigger manual analysis
        analyze_resp = await client.post(
            "/api/v1/learning/analyze",
            headers=headers,
            json={"profile_id": str(profile_id)},
        )
        assert analyze_resp.status_code == 200


@pytest.mark.asyncio
async def test_learning_api_multi_tenant_isolation():
    user_a = uuid4()
    user_b = uuid4()
    profile_a = uuid4()
    job_id = uuid4()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # User A records outcome
        await client.post(
            "/api/v1/learning/outcomes",
            headers={"Authorization": f"Bearer {user_a}"},
            json={
                "profile_id": str(profile_a),
                "job_id": str(job_id),
                "outcome_type": "OFFER",
                "notes": "Private offer letter details",
            },
        )

        # User B queries outcomes
        resp_b = await client.get(
            "/api/v1/learning/outcomes",
            headers={"Authorization": f"Bearer {user_b}"},
        )
        assert resp_b.status_code == 200
        assert len(resp_b.json()["data"]) == 0
