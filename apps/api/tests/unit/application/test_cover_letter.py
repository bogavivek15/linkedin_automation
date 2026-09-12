"""
Tests for Grounded Cover Letter Generation.
"""

from apps.api.app.domain.application.claims import VerifiedClaimIndex
from apps.api.app.domain.application.cover_letter import (
    generate_cover_letter_deterministic,
)
from apps.api.app.domain.application.models import JobRequirement


def test_cover_letter_generation_grounded_in_evidence():
    claim_index = VerifiedClaimIndex()
    claim_index.add_claim(
        {
            "id": "c_proj",
            "claim_type": "OUTCOME",
            "statement": "built a distributed cache service in Python",
            "source_type": "PROJECT",
            "evidence_text": "Built Redis clone with asyncio",
            "verification_status": "VERIFIED",
        }
    )
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

    profile_data = {
        "full_name": "Alex Student",
    }
    job_data = {
        "title": "Backend Systems Engineer",
        "company_name": "CloudScale Inc.",
    }
    job_requirements = [
        JobRequirement(
            text="Python proficiency",
            category="SKILL",
            importance="REQUIRED",
            normalized_value="python",
            evidence_source="skills",
        )
    ]

    letter, claim_ids = generate_cover_letter_deterministic(
        profile_data=profile_data,
        job_data=job_data,
        job_requirements=job_requirements,
        verified_claims=claim_index,
    )

    assert "CloudScale Inc." in letter
    assert "Backend Systems Engineer" in letter
    assert "Alex Student" in letter
    assert "built a distributed cache service in Python" in letter
    assert "c_proj" in claim_ids or "c_py" in claim_ids
