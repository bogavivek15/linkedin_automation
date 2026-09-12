import pytest
from apps.api.app.domain.job.models import CanonicalJob
from apps.api.app.domain.trust.models import (
    EvidenceCategory,
    EvidenceSentiment,
    EvidenceSeverity,
    TrustContext,
)
from apps.api.app.services.trust.providers.domain import DomainEvidenceProvider


@pytest.fixture
def base_job() -> CanonicalJob:
    return CanonicalJob(
        external_id="dom-job-1",
        source="HIMALAYAS",
        source_url="https://himalayas.app/jobs/swe-1",
        title="Software Engineer",
        normalized_title="software engineer",
        company_name="Acme Global",
        normalized_company="acme global",
        description="Software development role.",
        description_hash="hash-dom",
    )


@pytest.mark.asyncio
async def test_detects_major_brand_impersonation(base_job: CanonicalJob):
    base_job.company_name = "Google Inc."
    base_job.normalized_company = "google"
    base_job.application_url = "https://apply-google-careers.xyz/job/123"

    provider = DomainEvidenceProvider()
    context = TrustContext(job=base_job, company_name=base_job.company_name, application_url=base_job.application_url)

    evidence = await provider.collect(context)
    impersonation_evidence = [e for e in evidence if e.evidence_type == EvidenceCategory.IMPERSONATION.value]

    assert len(impersonation_evidence) >= 1
    assert impersonation_evidence[0].sentiment == EvidenceSentiment.NEGATIVE
    assert impersonation_evidence[0].severity == EvidenceSeverity.HIGH
    assert "brand impersonation" in impersonation_evidence[0].claim.lower()


@pytest.mark.asyncio
async def test_recognizes_verified_enterprise_ats_platform(base_job: CanonicalJob):
    base_job.application_url = "https://boards.greenhouse.io/acmetech/jobs/456"

    provider = DomainEvidenceProvider()
    context = TrustContext(job=base_job, company_name=base_job.company_name, application_url=base_job.application_url)

    evidence = await provider.collect(context)
    ats_evidence = [e for e in evidence if "recognized verified recruitment platform" in e.claim.lower()]

    assert len(ats_evidence) >= 1
    assert ats_evidence[0].sentiment == EvidenceSentiment.POSITIVE
    assert ats_evidence[0].severity == EvidenceSeverity.LOW


@pytest.mark.asyncio
async def test_flags_insecure_http_transport(base_job: CanonicalJob):
    base_job.application_url = "http://insecure-careers.com/job"

    provider = DomainEvidenceProvider()
    context = TrustContext(job=base_job, company_name=base_job.company_name, application_url=base_job.application_url)

    evidence = await provider.collect(context)
    insecure_evidence = [e for e in evidence if "insecure non-https transport" in e.claim.lower()]

    assert len(insecure_evidence) >= 1
    assert insecure_evidence[0].sentiment == EvidenceSentiment.NEGATIVE


@pytest.mark.asyncio
async def test_handles_missing_application_url_gracefully(base_job: CanonicalJob):
    base_job.application_url = None
    base_job.source_url = ""

    provider = DomainEvidenceProvider()
    context = TrustContext(job=base_job, company_name=base_job.company_name, application_url=None)

    evidence = await provider.collect(context)
    missing_evidence = [e for e in evidence if e.evidence_type == EvidenceCategory.MISSING_INFORMATION.value]

    assert len(missing_evidence) >= 1
