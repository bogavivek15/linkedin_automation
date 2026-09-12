"""
Tests for Application Package Assembly and Lifecycle States.
"""

from uuid import uuid4

from apps.api.app.domain.application.models import (
    ApplicationAnswer,
    ApplicationQuality,
    TailoredResume,
    ValidationResult,
)
from apps.api.app.domain.application.package import assemble_application_package


def test_package_assembly_ready_for_review():
    prof_id = str(uuid4())
    job_id = str(uuid4())
    resume_id = str(uuid4())

    tailored = TailoredResume(
        base_resume_id=resume_id,
        profile_id=prof_id,
        job_id=job_id,
        content="Tailored resume",
        changes=[],
    )
    val_res = ValidationResult(valid=True, confidence="HIGH")
    quality = ApplicationQuality(
        relevance_score=90.0,
        completeness_score=95.0,
        clarity_score=95.0,
        consistency_score=95.0,
        claim_safety_score=100.0,
        requirement_coverage_score=90.0,
        overall_score=94.0,
    )

    pkg = assemble_application_package(
        profile_id=prof_id,
        job_id=job_id,
        decision_id=None,
        decision_action="AUTO_APPLY",
        resume_id=resume_id,
        tailored_resume=tailored,
        cover_letter="My letter",
        answers=[],
        selected_skills=["python"],
        supporting_claim_ids=["c1"],
        validation_result=val_res,
        quality=quality,
    )

    assert pkg.validation_status == "READY_FOR_REVIEW"
    assert pkg.quality_status == "PASSED"
    assert len(pkg.blocking_issues) == 0


def test_package_assembly_requires_verification_on_unresolved_answers():
    prof_id = str(uuid4())
    job_id = str(uuid4())
    resume_id = str(uuid4())

    val_res = ValidationResult(valid=True, confidence="HIGH")
    quality = ApplicationQuality(
        relevance_score=80.0,
        completeness_score=75.0,
        clarity_score=95.0,
        consistency_score=95.0,
        claim_safety_score=100.0,
        requirement_coverage_score=80.0,
        overall_score=85.0,
    )
    unresolved_ans = ApplicationAnswer(
        question="Desired Salary?",
        answer="[UNSPECIFIED]",
        requires_verification=True,
    )

    pkg = assemble_application_package(
        profile_id=prof_id,
        job_id=job_id,
        decision_id=None,
        decision_action="USER_APPROVAL",
        resume_id=resume_id,
        tailored_resume=None,
        cover_letter="My letter",
        answers=[unresolved_ans],
        selected_skills=[],
        supporting_claim_ids=[],
        validation_result=val_res,
        quality=quality,
    )

    assert pkg.validation_status == "REQUIRES_VERIFICATION"


def test_package_assembly_blocked_on_reject_decision():
    prof_id = str(uuid4())
    job_id = str(uuid4())
    resume_id = str(uuid4())

    val_res = ValidationResult(valid=True)
    quality = ApplicationQuality(
        relevance_score=40.0,
        completeness_score=50.0,
        clarity_score=80.0,
        consistency_score=80.0,
        claim_safety_score=100.0,
        requirement_coverage_score=30.0,
        overall_score=50.0,
    )

    pkg = assemble_application_package(
        profile_id=prof_id,
        job_id=job_id,
        decision_id=None,
        decision_action="REJECT",
        resume_id=resume_id,
        tailored_resume=None,
        cover_letter=None,
        answers=[],
        selected_skills=[],
        supporting_claim_ids=[],
        validation_result=val_res,
        quality=quality,
    )

    assert pkg.validation_status == "BLOCKED"
    assert any("rejected by decision policy" in b for b in pkg.blocking_issues)
