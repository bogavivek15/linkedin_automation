"""
Tests for Resume Tailoring Engine and Change Diff Tracking.
"""

from uuid import uuid4

from apps.api.app.domain.application.claims import VerifiedClaimIndex
from apps.api.app.domain.application.models import JobRequirement
from apps.api.app.domain.application.resume import tailor_resume


def test_resume_tailoring_diff_and_claim_tracking():
    claim_index = VerifiedClaimIndex()
    c1 = {
        "id": "claim_python",
        "claim_type": "SKILL",
        "statement": "Python",
        "source_type": "PROJECT",
        "evidence_text": "Built data pipelines with Python",
        "verification_status": "VERIFIED",
    }
    c2 = {
        "id": "claim_fastapi",
        "claim_type": "SKILL",
        "statement": "FastAPI",
        "source_type": "PROJECT",
        "evidence_text": "Built REST endpoints with FastAPI",
        "verification_status": "VERIFIED",
    }
    claim_index.add_claim(c1)
    claim_index.add_claim(c2)

    base_resume = {
        "id": str(uuid4()),
        "raw_text": "SUMMARY\nSoftware Engineer.\nSKILLS\nPython, SQL\nEXPERIENCE\nBackend Dev\n",
        "sections": {
            "SUMMARY": "Software Engineer.",
            "SKILLS": "Python, SQL",
            "EXPERIENCE": "Backend Dev",
        },
    }

    job_requirements = [
        JobRequirement(
            text="Proficiency in Python",
            category="SKILL",
            importance="REQUIRED",
            normalized_value="python",
            evidence_source="job.req_skills",
        ),
        JobRequirement(
            text="Experience with FastAPI",
            category="SKILL",
            importance="REQUIRED",
            normalized_value="fastapi",
            evidence_source="job.req_skills",
        ),
    ]

    tailored = tailor_resume(
        base_resume=base_resume,
        job_requirements=job_requirements,
        verified_claims=claim_index,
        job_id=str(uuid4()),
        profile_id=str(uuid4()),
    )

    assert tailored.content is not None
    assert len(tailored.changes) > 0

    # Ensure changes have reasons and claim IDs
    for ch in tailored.changes:
        assert ch.reason != ""
        assert len(ch.supporting_claim_ids) > 0
        assert ch.section in ("SUMMARY", "SKILLS")

    # Check supporting claim IDs collected on the tailored resume
    assert "claim_python" in tailored.supporting_claim_ids
    assert "claim_fastapi" in tailored.supporting_claim_ids
