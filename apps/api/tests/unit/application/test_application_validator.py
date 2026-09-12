"""
Tests for Deterministic Application Package Validator.
"""

from uuid import uuid4

from apps.api.app.domain.application.claims import VerifiedClaimIndex
from apps.api.app.domain.application.models import (
    ApplicationAnswer,
    ApplicationPackage,
    ResumeChange,
    TailoredResume,
)
from apps.api.app.domain.application.validator import validate_application_package


def test_validator_detects_invented_metric():
    claim_index = VerifiedClaimIndex()
    claim_index.add_claim(
        {
            "id": "c1",
            "claim_type": "SKILL",
            "statement": "Python",
            "source_type": "PROJECT",
            "evidence_text": "Python programming",
            "verification_status": "VERIFIED",
        }
    )

    package = ApplicationPackage(
        profile_id=str(uuid4()),
        job_id=str(uuid4()),
        resume_id=str(uuid4()),
        tailored_resume=TailoredResume(
            base_resume_id=str(uuid4()),
            profile_id=str(uuid4()),
            job_id=str(uuid4()),
            content="Engineered system that achieved 400% improvement in throughput.",
            changes=[],
            supporting_claim_ids=["c1"],
        ),
        cover_letter="I achieved 400% improvement in performance.",
        application_answers=[],
        selected_skills=["python"],
        supporting_claim_ids=["c1"],
    )

    res = validate_application_package(package, claim_index)
    assert res.valid is False
    assert any("Invented quantitative metric" in u for u in res.unsupported_claims)
    assert any("400%" in b for b in res.blocking_issues)


def test_validator_detects_unsupported_leadership():
    claim_index = VerifiedClaimIndex()
    claim_index.add_claim(
        {
            "id": "c1",
            "claim_type": "SKILL",
            "statement": "Python",
            "source_type": "PROJECT",
            "evidence_text": "Built solo backend project",
            "verification_status": "VERIFIED",
        }
    )

    package = ApplicationPackage(
        profile_id=str(uuid4()),
        job_id=str(uuid4()),
        resume_id=str(uuid4()),
        tailored_resume=TailoredResume(
            base_resume_id=str(uuid4()),
            profile_id=str(uuid4()),
            job_id=str(uuid4()),
            content="Led a team of 8 engineers to deploy microservices.",
            changes=[],
            supporting_claim_ids=["c1"],
        ),
        cover_letter="I led a team of 8 engineers.",
        application_answers=[],
        selected_skills=["python"],
        supporting_claim_ids=["c1"],
    )

    res = validate_application_package(package, claim_index)
    assert res.valid is False
    assert any("Unsupported leadership claim" in u for u in res.unsupported_claims)


def test_validator_accepts_verified_evidence():
    claim_index = VerifiedClaimIndex()
    claim_index.add_claim(
        {
            "id": "c_py",
            "claim_type": "SKILL",
            "statement": "Python",
            "source_type": "PROJECT",
            "evidence_text": "Python development",
            "verification_status": "VERIFIED",
        }
    )

    package = ApplicationPackage(
        profile_id=str(uuid4()),
        job_id=str(uuid4()),
        resume_id=str(uuid4()),
        tailored_resume=TailoredResume(
            base_resume_id=str(uuid4()),
            profile_id=str(uuid4()),
            job_id=str(uuid4()),
            content="Software engineer proficient in Python development.",
            changes=[
                ResumeChange(
                    section="SUMMARY",
                    original_text="Engineer",
                    proposed_text="Software engineer proficient in Python development",
                    reason="Emphasize verified Python skill",
                    supporting_claim_ids=["c_py"],
                )
            ],
            supporting_claim_ids=["c_py"],
        ),
        cover_letter="My verified background is in Python.",
        application_answers=[
            ApplicationAnswer(
                question="Why this role?",
                answer="I want to apply my Python skills.",
                question_type="MOTIVATION",
                supporting_claim_ids=["c_py"],
                confidence="HIGH",
                requires_verification=False,
            )
        ],
        selected_skills=["python"],
        supporting_claim_ids=["c_py"],
    )

    res = validate_application_package(package, claim_index)
    assert res.valid is True
    assert len(res.blocking_issues) == 0
    assert "c_py" in res.verified_claim_ids
