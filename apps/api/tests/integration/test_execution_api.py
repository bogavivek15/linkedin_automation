"""
CareerOS Phase 11 — Controlled Application Execution REST API Integration Tests.

Tests endpoints:
POST /api/v1/executions
GET  /api/v1/executions/{execution_id}
GET  /api/v1/executions/{execution_id}/events
GET  /api/v1/applications/{application_id}/execution
POST /api/v1/executions/{execution_id}/handoff-open
POST /api/v1/executions/{execution_id}/mark-submitted
POST /api/v1/executions/{execution_id}/cancel
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from apps.api.app.domain.application.models import (
    ApplicationAnswer,
    ApplicationPackage,
    ApplicationQuality,
)
from apps.api.app.domain.job.models import CanonicalJob
from apps.api.app.main import app
from apps.api.app.repositories.application_repository import ApplicationRepository
from apps.api.app.repositories.execution_repository import ExecutionRepository
from apps.api.app.repositories.job_repository import JobRepository
from httpx import ASGITransport, AsyncClient


@pytest.fixture(autouse=True)
def reset_stores():
    ExecutionRepository.reset_store()
    ApplicationRepository.reset_store()
    JobRepository.reset_store()


@pytest.mark.asyncio
async def test_execution_api_full_workflow():
    user_id = uuid4()
    job_id = uuid4()
    pkg_id = uuid4()

    # 1. Seed job and approved application package
    job = CanonicalJob(
        id=job_id,
        source="lever",
        source_url="https://acme.inc/jobs/apply",
        external_id="lever-202",
        title="Software Engineer",
        normalized_title="software engineer",
        company_name="Acme Inc",
        normalized_company="acme inc",
        description="Python backend developer",
        description_hash="hash_202",
        application_url="https://acme.inc/jobs/apply",
        status="ACTIVE",
    )
    await JobRepository.save_job(job)

    pkg = ApplicationPackage(
        id=str(pkg_id),
        profile_id=str(uuid4()),
        job_id=str(job_id),
        validation_status="APPROVED",
        quality_status="PASSED",
        cover_letter="Cover letter content",
        application_answers=[
            ApplicationAnswer(question="Why Acme?", answer="Great culture"),
        ],
        quality=ApplicationQuality(
            relevance_score=90.0,
            completeness_score=90.0,
            clarity_score=90.0,
            consistency_score=90.0,
            claim_safety_score=100.0,
            requirement_coverage_score=90.0,
            overall_score=90.0,
        ),
        package_version="v1",
        created_at=datetime.now(timezone.utc),
    )
    await ApplicationRepository.save_package(pkg, user_id)

    headers = {"Authorization": f"Bearer {user_id}"}
    idemp_key = f"key-{uuid4()}"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 2. POST /api/v1/executions
        res_exec = await ac.post(
            "/api/v1/executions",
            headers={**headers, "Idempotency-Key": idemp_key},
            json={"package_id": str(pkg_id), "requested_mode": "USER_HANDOFF"},
        )
        assert res_exec.status_code == 200
        data = res_exec.json()["data"]
        exec_id = data["id"]
        assert data["status"] == "USER_HANDOFF"
        assert data["execution_mode"] == "USER_HANDOFF"
        assert data["idempotency_key"] == idemp_key

        # 3. Idempotency Test: re-issuing exact request returns same execution
        res_idemp = await ac.post(
            "/api/v1/executions",
            headers={**headers, "Idempotency-Key": idemp_key},
            json={"package_id": str(pkg_id)},
        )
        assert res_idemp.status_code == 200
        assert res_idemp.json()["data"]["id"] == exec_id

        # 4. GET /api/v1/executions/{execution_id}
        res_get = await ac.get(f"/api/v1/executions/{exec_id}", headers=headers)
        assert res_get.status_code == 200
        assert res_get.json()["data"]["id"] == exec_id

        # 5. GET /api/v1/applications/{application_id}/execution
        res_pkg_exec = await ac.get(f"/api/v1/applications/{pkg_id}/execution", headers=headers)
        assert res_pkg_exec.status_code == 200
        assert res_pkg_exec.json()["data"]["id"] == exec_id

        # 6. POST /api/v1/executions/{execution_id}/handoff-open
        res_open = await ac.post(f"/api/v1/executions/{exec_id}/handoff-open", headers=headers)
        assert res_open.status_code == 200
        assert res_open.json()["data"]["handoff_details"]["opened_at"] is not None

        # 7. POST /api/v1/executions/{execution_id}/mark-submitted
        res_sub = await ac.post(
            f"/api/v1/executions/{exec_id}/mark-submitted",
            headers=headers,
            json={"notes": "External portal form completed"},
        )
        assert res_sub.status_code == 200
        sub_data = res_sub.json()["data"]
        assert sub_data["status"] == "SUBMITTED"
        assert sub_data["receipt"]["is_user_assertion"] is True
        assert sub_data["receipt"]["evidence_type"] == "USER_ASSERTION"

        # 8. GET /api/v1/executions/{execution_id}/events
        res_ev = await ac.get(f"/api/v1/executions/{exec_id}/events", headers=headers)
        assert res_ev.status_code == 200
        ev_types = [e["event_type"] for e in res_ev.json()["data"]]
        assert "EXECUTION_STARTED" in ev_types
        assert "HANDOFF_CREATED" in ev_types
        assert "HANDOFF_OPENED" in ev_types
        assert "USER_MARKED_SUBMITTED" in ev_types

        # 9. Cross-user isolation: Another user cannot access execution
        other_headers = {"Authorization": f"Bearer {uuid4()}"}
        res_forbidden = await ac.get(f"/api/v1/executions/{exec_id}", headers=other_headers)
        assert res_forbidden.status_code == 404
