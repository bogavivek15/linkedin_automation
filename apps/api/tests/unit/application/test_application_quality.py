"""
Tests for Application Quality Engine and Coverage Breakdown.
"""

from uuid import uuid4

from apps.api.app.domain.application.claims import VerifiedClaimIndex
from apps.api.app.domain.application.models import (
    ApplicationPackage,
    JobRequirement,
    TailoredResume,
    ValidationResult,
)
from apps.api.app.domain.application.quality import evaluate_application_quality


def test_quality_scoring_coverage_and_safety():
    claim_index = VerifiedClaimIndex()
    claim_index.add_claim(
        {
            "id": "c1",
            "claim_type": "SKILL",
            "statement": "Python",
            "source_type": "PROJECT",
            "evidence_text": "Python backend",
            "verification_status": "VERIFIED",
        }
    )

    job_reqs = [
        JobRequirement(
            text="Python",
            category="SKILL",
            importance="REQUIRED",
            normalized_value="python",
            evidence_source="job.req",
        ),
        JobRequirement(
            text="Docker",
            category="SKILL",
            importance="REQUIRED",
            normalized_value="docker",
            evidence_source="job.req",
        ),
    ]

    package = ApplicationPackage(
        profile_id=str(uuid4()),
        job_id=str(uuid4()),
        resume_id=str(uuid4()),
        tailored_resume=TailoredResume(
            base_resume_id=str(uuid4()),
            profile_id=str(uuid4()),
            job_id=str(uuid4()),
            content="Tailored resume text",
            changes=[],
            supporting_claim_ids=["c1"],
        ),
        cover_letter="Cover letter text",
        application_answers=[],
        selected_skills=["python"],
        supporting_claim_ids=["c1"],
    )

    val_result = ValidationResult(
        valid=True,
        verified_claim_ids=["c1"],
        unsupported_claims=[],
        warnings=[],
        blocking_issues=[],
        confidence="HIGH",
    )

    quality = evaluate_application_quality(package, job_reqs, claim_index, val_result)

    assert quality.claim_safety_score == 100.0
    assert quality.coverage is not None
    # 1 of 2 required skills covered -> 50%
    assert quality.coverage.coverage_percentage == 50.0
    assert len(quality.coverage.required_addressed) == 1
    assert len(quality.coverage.required_missing) == 1
    assert quality.overall_score > 0
