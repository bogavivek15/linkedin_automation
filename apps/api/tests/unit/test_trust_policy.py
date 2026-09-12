from datetime import datetime, timezone
from uuid import uuid4

import pytest
from apps.api.app.domain.job.models import CanonicalJob
from apps.api.app.domain.trust.models import (
    ConfidenceLevel,
    EvidenceCategory,
    EvidenceSentiment,
    EvidenceSeverity,
    RiskLevel,
    TrustContext,
    TrustEvidence,
)
from apps.api.app.services.trust.policy import TrustPolicyEngine


@pytest.fixture
def base_job() -> CanonicalJob:
    return CanonicalJob(
        id=uuid4(),
        external_id="test-job-pol-1",
        source="HIMALAYAS",
        source_url="https://himalayas.app/jobs/test",
        title="Staff Platform Engineer",
        normalized_title="staff platform engineer",
        company_name="Acme Global",
        normalized_company="acme global",
        description="Engineering role details.",
        description_hash="hash-pol-1",
    )


def test_scoring_boundaries(base_job: CanonicalJob):
    context = TrustContext(job=base_job, company_name=base_job.company_name)

    # Empty evidence
    assessment = TrustPolicyEngine.evaluate([], context)
    assert 0.0 <= assessment.trust_score <= 100.0
    assert 0.0 <= assessment.risk_score <= 100.0
    assert assessment.risk_level == RiskLevel.UNKNOWN
    assert assessment.confidence == ConfidenceLevel.LOW

    # Enormous penalty
    huge_penalties = [
        TrustEvidence(
            evidence_type=EvidenceCategory.PAYMENT_REQUEST.value,
            source_name="RuleEngine",
            claim=f"Penalty {i}",
            sentiment=EvidenceSentiment.NEGATIVE,
            severity=EvidenceSeverity.HIGH,
            retrieved_at=datetime.now(timezone.utc),
        )
        for i in range(10)
    ]
    assessment_pen = TrustPolicyEngine.evaluate(huge_penalties, context)
    assert 0.0 <= assessment_pen.trust_score <= 100.0
    assert 0.0 <= assessment_pen.risk_score <= 100.0
    assert assessment_pen.risk_level == RiskLevel.HIGH


def test_severe_scam_payment_demand_triggers_high_risk(base_job: CanonicalJob):
    context = TrustContext(job=base_job, company_name=base_job.company_name)
    evidence = [
        TrustEvidence(
            evidence_type=EvidenceCategory.PAYMENT_REQUEST.value,
            source_name="CareerOS deterministic analysis",
            claim="Job description requires an upfront registration fee",
            sentiment=EvidenceSentiment.NEGATIVE,
            severity=EvidenceSeverity.HIGH,
            retrieved_at=datetime.now(timezone.utc),
        )
    ]

    assessment = TrustPolicyEngine.evaluate(evidence, context)
    assert assessment.risk_level == RiskLevel.HIGH
    assert assessment.trust_score <= 18.0
    assert assessment.risk_score >= 90.0
    assert "upfront registration fee" in assessment.suspicious_signals[0]


def test_brand_impersonation_triggers_high_risk(base_job: CanonicalJob):
    context = TrustContext(job=base_job, company_name="Google")
    evidence = [
        TrustEvidence(
            evidence_type=EvidenceCategory.IMPERSONATION.value,
            source_name="CareerOS Domain Intelligence",
            claim="Application URL uses suspicious domain for Google",
            sentiment=EvidenceSentiment.NEGATIVE,
            severity=EvidenceSeverity.HIGH,
            retrieved_at=datetime.now(timezone.utc),
        )
    ]

    assessment = TrustPolicyEngine.evaluate(evidence, context)
    assert assessment.risk_level == RiskLevel.HIGH
    assert assessment.trust_score <= 18.0
    assert assessment.risk_score == 92.0


def test_insufficient_evidence_results_in_unknown_risk(base_job: CanonicalJob):
    context = TrustContext(job=base_job, company_name="Obscure Startup")
    evidence = [
        TrustEvidence(
            evidence_type=EvidenceCategory.MISSING_INFORMATION.value,
            source_name="CareerOS deterministic analysis",
            claim="No verified company website found",
            sentiment=EvidenceSentiment.NEUTRAL,
            severity=EvidenceSeverity.LOW,
            retrieved_at=datetime.now(timezone.utc),
        )
    ]

    assessment = TrustPolicyEngine.evaluate(evidence, context)
    # Crucial Phase 7 requirement: UNKNOWN must be distinct from LOW risk
    assert assessment.risk_level == RiskLevel.UNKNOWN
    assert assessment.confidence == ConfidenceLevel.LOW
    assert len(assessment.missing_information) == 1


def test_conflicting_evidence_lowers_confidence(base_job: CanonicalJob):
    context = TrustContext(job=base_job, company_name="Acme Corp")
    evidence = [
        TrustEvidence(
            evidence_type=EvidenceCategory.COMPANY_IDENTITY.value,
            source_name="Public Registry",
            claim="Verified company filing",
            sentiment=EvidenceSentiment.POSITIVE,
            severity=EvidenceSeverity.LOW,
            retrieved_at=datetime.now(timezone.utc),
        ),
        TrustEvidence(
            evidence_type=EvidenceCategory.PAYMENT_REQUEST.value,
            source_name="CareerOS deterministic analysis",
            claim="Suspicious wire transfer required",
            sentiment=EvidenceSentiment.NEGATIVE,
            severity=EvidenceSeverity.HIGH,
            retrieved_at=datetime.now(timezone.utc),
        ),
    ]

    assessment = TrustPolicyEngine.evaluate(evidence, context)
    assert assessment.risk_level == RiskLevel.HIGH
    assert assessment.confidence == ConfidenceLevel.LOW
    assert len(assessment.positive_signals) >= 1
    assert len(assessment.suspicious_signals) >= 1


def test_strong_evidence_yields_low_risk_high_confidence(base_job: CanonicalJob):
    context = TrustContext(job=base_job, company_name="Stripe")
    evidence = [
        TrustEvidence(
            evidence_type=EvidenceCategory.APPLICATION_DOMAIN.value,
            source_name="CareerOS Domain Intelligence",
            claim="Application URL matches official company domain stripe.com",
            sentiment=EvidenceSentiment.POSITIVE,
            severity=EvidenceSeverity.LOW,
            retrieved_at=datetime.now(timezone.utc),
        ),
        TrustEvidence(
            evidence_type=EvidenceCategory.DOMAIN.value,
            source_name="CareerOS Domain Intelligence",
            claim="Secure HTTPS transport verified",
            sentiment=EvidenceSentiment.POSITIVE,
            severity=EvidenceSeverity.LOW,
            retrieved_at=datetime.now(timezone.utc),
        ),
        TrustEvidence(
            evidence_type=EvidenceCategory.JOB_DESCRIPTION.value,
            source_name="CareerOS deterministic analysis",
            claim="Comprehensive job description with clear responsibilities",
            sentiment=EvidenceSentiment.POSITIVE,
            severity=EvidenceSeverity.LOW,
            retrieved_at=datetime.now(timezone.utc),
        ),
        TrustEvidence(
            evidence_type=EvidenceCategory.COMPANY_IDENTITY.value,
            source_name="Public Registry",
            claim="Official entity registration verified",
            sentiment=EvidenceSentiment.POSITIVE,
            severity=EvidenceSeverity.LOW,
            retrieved_at=datetime.now(timezone.utc),
        ),
    ]

    assessment = TrustPolicyEngine.evaluate(evidence, context)
    assert assessment.risk_level == RiskLevel.LOW
    assert assessment.confidence == ConfidenceLevel.HIGH
    assert assessment.trust_score >= 80.0
    assert assessment.risk_score <= 20.0
    assert len(assessment.suspicious_signals) == 0
    assert len(assessment.positive_signals) == 4


def test_versioning_and_explanation(base_job: CanonicalJob):
    context = TrustContext(job=base_job, company_name="Acme Global")
    assessment = TrustPolicyEngine.evaluate([], context, assessment_version="v2")

    assert assessment.assessment_version == "v2"
    assert "Acme Global" in assessment.explanation
    assert "INSUFFICIENT EVIDENCE" in assessment.explanation
    assert assessment.job_id == base_job.id
