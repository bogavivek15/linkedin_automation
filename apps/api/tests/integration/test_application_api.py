"""
CareerOS Phase 10 — Application Intelligence REST API Integration Tests.

Tests endpoints:
POST /api/v1/applications/prepare
GET  /api/v1/applications
GET  /api/v1/applications/{application_id}
GET  /api/v1/jobs/{job_id}/application
POST /api/v1/applications/{application_id}/validate
POST /api/v1/applications/{application_id}/approve
POST /api/v1/applications/{application_id}/regenerate
"""

from uuid import uuid4

import pytest
from apps.api.app.domain.decision.models import Decision
from apps.api.app.domain.job.models import CanonicalJob
from apps.api.app.domain.matching.models import (
    ProfileSkillRecord,
    UserPreferencesRecord,
)
from apps.api.app.main import app
from apps.api.app.repositories.application_repository import ApplicationRepository
from apps.api.app.repositories.decision_repository import DecisionRepository
from apps.api.app.repositories.job_repository import JobRepository
from apps.api.app.repositories.profile_repository import ProfileRepository
from apps.api.app.repositories.resume_repository import ResumeRepository
from httpx import ASGITransport, AsyncClient


@pytest.fixture(autouse=True)
def reset_all_stores():
    ApplicationRepository.reset_store()
    DecisionRepository.reset_store()
    JobRepository.reset_store()
    ProfileRepository.reset_store()
    ResumeRepository.reset_store()


@pytest.mark.asyncio
async def test_application_api_full_lifecycle():
    user_id = uuid4()
    profile_id = uuid4()
    job_id = uuid4()

    # 1. Seed Profile, Skills, Preferences
    await ProfileRepository.save_profile(
        profile_id=profile_id,
        user_id=user_id,
        full_name="Maya Lin",
        headline="Full Stack Engineer",
        career_summary="Passionate builder of robust web APIs and React frontends.",
    )
    await ProfileRepository.save_profile_skill(
        ProfileSkillRecord(
            profile_id=profile_id,
            user_id=user_id,
            skill_name="Python",
            normalized_name="python",
            proficiency="EXPERT",
            years_experience=3.0,
            verified_status="VERIFIED",
            source="PROJECT",
        )
    )
    await ProfileRepository.save_profile_skill(
        ProfileSkillRecord(
            profile_id=profile_id,
            user_id=user_id,
            skill_name="FastAPI",
            normalized_name="fastapi",
            proficiency="ADVANCED",
            years_experience=2.0,
            verified_status="VERIFIED",
            source="PROJECT",
        )
    )
    await ProfileRepository.save_preferences(
        UserPreferencesRecord(
            profile_id=profile_id,
            user_id=user_id,
            minimum_salary=100000.0,
            work_authorization="Authorized to work in US without restriction",
        )
    )

    # 2. Seed Canonical Job
    await JobRepository.save_job(
        CanonicalJob(
            id=job_id,
            source="greenhouse",
            source_url=f"https://example.com/jobs/{job_id}",
            external_id="gh_101",
            title="Senior Backend Engineer",
            normalized_title="senior backend engineer",
            company_name="Veloce AI",
            normalized_company="veloce ai",
            required_skills=["Python", "FastAPI"],
            preferred_skills=["PostgreSQL"],
            description="Seeking backend engineer. Question 1: What is your experience with FastAPI?",
            description_hash="desc_hash_101",
        )
    )

    # 3. Seed Decision (AUTO_APPLY)
    await DecisionRepository.save_decision(
        Decision(
            profile_id=profile_id,
            job_id=job_id,
            overall_score=94.0,
            match_score=95.0,
            trust_score=91.0,
            action="AUTO_APPLY",
        ),
        user_id=user_id,
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        headers = {"X-User-Id": str(user_id)}

        # A. Prepare Application Package
        prepare_payload = {
            "profile_id": str(profile_id),
            "job_id": str(job_id),
        }
        resp = await ac.post("/api/v1/applications/prepare", json=prepare_payload, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        package = data["data"]
        pkg_id = package["id"]
        assert package["validation_status"] == "READY_FOR_REVIEW"
        assert package["quality_status"] == "PASSED"
        assert package["tailored_resume"] is not None
        assert package["cover_letter"] is not None
        assert len(package["application_answers"]) > 0

        # B. List Application Packages
        list_resp = await ac.get("/api/v1/applications", headers=headers)
        assert list_resp.status_code == 200
        pkgs = list_resp.json()["data"]
        assert len(pkgs) == 1
        assert pkgs[0]["id"] == pkg_id

        # C. Get Single Application Package
        get_resp = await ac.get(f"/api/v1/applications/{pkg_id}", headers=headers)
        assert get_resp.status_code == 200
        assert get_resp.json()["data"]["id"] == pkg_id

        # D. Get Application for Job
        job_pkg_resp = await ac.get(f"/api/v1/jobs/{job_id}/application", headers=headers)
        assert job_pkg_resp.status_code == 200
        assert job_pkg_resp.json()["data"]["id"] == pkg_id

        # E. Validate Application Package
        val_resp = await ac.post(f"/api/v1/applications/{pkg_id}/validate", headers=headers)
        assert val_resp.status_code == 200
        val_data = val_resp.json()["data"]
        assert val_data["validation"]["valid"] is True
        assert val_data["quality"]["claim_safety_score"] == 100.0

        # F. User Approves Application Package (transitions READY_FOR_REVIEW -> APPROVED)
        approve_resp = await ac.post(f"/api/v1/applications/{pkg_id}/approve", headers=headers)
        assert approve_resp.status_code == 200
        appr_data = approve_resp.json()
        assert appr_data["data"]["validation_status"] == "APPROVED"

        # G. Regenerate Application Package
        regen_payload = {"instructions": "Emphasize high throughput backend systems"}
        regen_resp = await ac.post(f"/api/v1/applications/{pkg_id}/regenerate", json=regen_payload, headers=headers)
        assert regen_resp.status_code == 200
        regen_data = regen_resp.json()["data"]
        assert regen_data["package_version"] == "v2"

        # H. Security / Isolation: Other user cannot access package
        other_headers = {"X-User-Id": str(uuid4())}
        sec_get = await ac.get(f"/api/v1/applications/{pkg_id}", headers=other_headers)
        assert sec_get.status_code == 404

        sec_approve = await ac.post(f"/api/v1/applications/{pkg_id}/approve", headers=other_headers)
        assert sec_approve.status_code == 404
