from uuid import uuid4
from unittest.mock import AsyncMock, patch

import pytest

from apps.api.app.domain.job.gemini_search import GeminiOpportunityAgent
from apps.api.app.domain.job.models import CanonicalJob
from apps.api.app.domain.presence.gemini_generator import generate_presence_post
from apps.api.app.domain.trust.models import (
    EvidenceCategory,
    EvidenceSentiment,
    EvidenceSeverity,
    RiskLevel,
    TrustContext,
    TrustEvidence,
)
from apps.api.app.domain.trust.policy import TrustPolicy
from apps.api.app.repositories.application_repository import ApplicationRepository
from apps.api.app.repositories.job_repository import JobRepository
from apps.api.app.repositories.network_repository import NetworkRepository
from apps.api.app.repositories.presence_repository import PresenceRepository


def _job(description: str, company: str = "Acme") -> CanonicalJob:
    return CanonicalJob(
        external_id=str(uuid4()),
        source="TEST",
        source_url="https://example.com/job",
        title="Software Engineer",
        normalized_title="software engineer",
        company_name=company,
        normalized_company=company.lower(),
        description=description,
        description_hash="testhash",
        application_url="https://example.com/apply",
    )


@pytest.mark.asyncio
async def test_trust_agent_rejects_upfront_payment_without_gemini():
    job = _job("Urgent hiring! You must pay $150 upfront for licensing software before onboarding.")
    context = TrustContext(job=job, company_name=job.company_name, application_url=job.application_url)
    with patch("apps.api.app.domain.trust.policy.collect_gemini_evidence", return_value=[]):
        assessment = await TrustPolicy().evaluate_opportunity(context)
    assert assessment.risk_level == RiskLevel.HIGH
    assert not TrustPolicy.is_trusted(assessment)
    assert any("upfront" in s.lower() or "payment" in s.lower() or "fee" in s.lower() for s in assessment.suspicious_signals)


@pytest.mark.asyncio
async def test_trust_agent_accepts_clean_job_when_gemini_returns_positive_evidence():
    job = _job("Backend role building APIs. Apply on the company careers page.")
    context = TrustContext(job=job, company_name=job.company_name, application_url="https://acme.example/careers")
    gemini_evidence = [
        TrustEvidence(
            evidence_type=EvidenceCategory.COMPANY_IDENTITY.value,
            source_name="Gemini posting analysis",
            claim="Company careers URL is consistent with the company name",
            sentiment=EvidenceSentiment.POSITIVE,
            severity=EvidenceSeverity.LOW,
        )
    ]
    with patch("apps.api.app.domain.trust.policy.collect_gemini_evidence", return_value=gemini_evidence):
        assessment = await TrustPolicy().evaluate_opportunity(context)
    assert TrustPolicy.is_trusted(assessment)
    assert assessment.risk_level != RiskLevel.HIGH


def test_presence_agent_returns_text_from_resume_context():
    post = generate_presence_post("user-1", "profile-1", "Built a FastAPI orchestrator with pgvector memory.")
    assert post.content_body
    assert "FastAPI" in post.content_body or "milestone" in post.content_body.lower()
    assert post.publication_mode == "USER_HANDOFF"


def test_opportunity_fallback_includes_scam_and_trusted_roles():
    jobs = GeminiOpportunityAgent()._fallback_jobs("AI Engineer, ML Engineer", "San Francisco")
    assert len(jobs) == 3
    assert any("pay $150" in j.description.lower() or "upfront" in j.description.lower() for j in jobs)
    assert any("deepmind" in j.company_name.lower() or "anthropic" in j.company_name.lower() for j in jobs)


@pytest.mark.asyncio
async def test_orchestrator_cycle_filters_jobs_and_creates_packages(monkeypatch):
    JobRepository.reset_store()
    ApplicationRepository.reset_store()
    PresenceRepository.reset_store()
    NetworkRepository.reset_store()

    from apps.api.app.domain.orchestrator.workflow import OrchestratorWorkflow

    agent = GeminiOpportunityAgent()
    jobs = agent._fallback_jobs("AI Engineer", "Remote")

    monkeypatch.setattr(
        "apps.api.app.domain.orchestrator.workflow.opportunity_agent.search_jobs",
        lambda *_args, **_kwargs: jobs,
    )
    monkeypatch.setattr(
        "apps.api.app.domain.orchestrator.workflow.opportunity_agent.persist_jobs",
        AsyncMock(side_effect=lambda found: found),
    )
    monkeypatch.setattr(
        "apps.api.app.domain.orchestrator.workflow.presence_scheduler.schedule_daily_post",
        lambda **_kwargs: None,
    )

    with patch("apps.api.app.domain.trust.policy.collect_gemini_evidence", return_value=[]):
        result = await OrchestratorWorkflow().run_automation_cycle(
            user_id="test_user",
            profile_id="test_profile",
            resume_context="Senior engineer. Python, FastAPI, pgvector.",
            target_roles="AI Engineer",
            locations="Remote",
        )

    assert result["status"] == "success"
    assert result["jobs_discovered"] == 3
    assert result["trusted_jobs_count"] >= 1
    assert result["applications_prepared"] == result["trusted_jobs_count"]
    assert any("Apex" in name or "Entry" in name for name in result["rejected_jobs"]) or result["trusted_jobs_count"] < 3
    assert result["presence_post_id"]
