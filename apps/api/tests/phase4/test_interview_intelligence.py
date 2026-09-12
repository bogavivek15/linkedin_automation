"""
Tests for CareerOS Phase 4 Grounded Interview Intelligence Engine.
"""

import pytest
from uuid import uuid4
from apps.api.app.domain.application_lifecycle.interview import InterviewIntelligenceEngine
from apps.api.app.repositories.job_repository import JobRepository
from apps.api.app.repositories.lifecycle_repository import LifecycleRepository
from apps.api.app.repositories.profile_repository import ProfileRepository
from apps.api.app.services.lifecycle.service import LifecycleService
from apps.api.app.domain.job.models import CanonicalJob


def test_interview_intelligence_plan_generation_grounding():
    plan = InterviewIntelligenceEngine.generate_plan(
        lifecycle_id="lc-123",
        application_id="app-123",
        user_id="usr-123",
        job_id="job-123",
        company_name="Google DeepMind",
        role_title="AI Engineer",
        stage="TECHNICAL",
        job_requirements=["Python", "FastAPI", "Docker", "pgvector"],
        verified_skills=["Python", "FastAPI"],
        missing_skills=["Docker"],
        project_claims=[
            {"title": "CareerOS Agent Loop", "provenance": "GitHub repository bogavivek15/game_score"}
        ],
    )

    assert plan.stage == "TECHNICAL"
    assert plan.company_name == "Google DeepMind"
    assert plan.role_title == "AI Engineer"
    assert plan.overall_readiness in ("HIGH", "MEDIUM")

    # Verify project evidence is preserved
    assert len(plan.key_project_evidence) >= 1
    assert "CareerOS Agent Loop" in plan.key_project_evidence[0]

    # Verify gap warning is generated
    assert any("Docker" in w for w in plan.warning_areas)

    # Verify suggested questions and talking points
    assert len(plan.suggested_practice_questions) >= 1
    assert len(plan.talking_points) >= 1


@pytest.mark.asyncio
async def test_lifecycle_transition_triggers_interview_plan():
    user_id = uuid4()
    job_id = uuid4()
    app_id = uuid4()

    # Save job
    job = CanonicalJob(
        id=job_id,
        external_id="ext-job-test",
        source="TEST",
        source_url="https://example.com",
        title="Software Engineer",
        normalized_title="software engineer",
        company_name="Acme AI",
        normalized_company="acme ai",
        description="Python backend engineering role.",
        description_hash="hash123",
        required_skills=["Python", "FastAPI"],
    )
    await JobRepository.save_job(job)

    lc_service = LifecycleService()
    lc = await lc_service.get_or_create_lifecycle(app_id, user_id, job_id, initial_status="SCREENING")

    # Transition to INTERVIEW
    updated_lc, trans = await lc_service.transition_status(
        lifecycle_id=lc.id,
        user_id=user_id,
        to_status="INTERVIEW",
        evidence_type="RECRUITER_COMMUNICATION",
        notes="Technical interview invitation",
    )

    assert updated_lc.current_status == "INTERVIEW"
    assert "interview_prep_plan" in updated_lc.metadata
    prep_plan = updated_lc.metadata["interview_prep_plan"]
    assert prep_plan["stage"] == "INTERVIEW"
    assert prep_plan["company_name"] == "Acme AI"
