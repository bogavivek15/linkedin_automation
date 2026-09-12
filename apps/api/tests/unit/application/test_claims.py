"""
Tests for Verified Claim Index and Provenance.
"""

from uuid import uuid4

from apps.api.app.domain.application.claims import VerifiedClaimIndex
from apps.api.app.domain.resume.models import ResumeClaim


def test_verified_claim_index_admittance():
    index = VerifiedClaimIndex()
    resume_id = uuid4()

    # 1. Verified claim - accepted
    verified_claim = ResumeClaim(
        resume_id=resume_id,
        claim_type="SKILL",
        statement="Python",
        source_type="PROJECT",
        evidence_text="Built backend using Python",
        verification_status="VERIFIED",
        allowed_in_tailoring=True,
    )
    assert index.add_claim(verified_claim) is True
    assert index.is_skill_verified("Python") is True
    assert index.is_claim_verified(str(verified_claim.id)) is True

    # 2. Inferred claim - rejected as factual evidence
    inferred_claim = ResumeClaim(
        resume_id=resume_id,
        claim_type="SKILL",
        statement="Kubernetes",
        source_type="PROJECT",
        evidence_text="Mentioned containerized deployment",
        verification_status="INFERRED",
        allowed_in_tailoring=False,
    )
    assert index.add_claim(inferred_claim) is False
    assert index.is_skill_verified("Kubernetes") is False
    assert index.is_claim_verified(str(inferred_claim.id)) is False

    # 3. Uncertain claim - rejected
    uncertain_claim = ResumeClaim(
        resume_id=resume_id,
        claim_type="METRIC",
        statement="Improved latency by 50%",
        source_type="EXPERIENCE",
        evidence_text="Claims fast API",
        verification_status="UNCERTAIN",
        allowed_in_tailoring=False,
    )
    assert index.add_claim(uncertain_claim) is False


def test_verified_claim_finding_support():
    index = VerifiedClaimIndex()
    c1 = {
        "id": "c1",
        "claim_type": "SKILL",
        "statement": "FastAPI",
        "source_type": "PROJECT",
        "evidence_text": "Built high-performance API with FastAPI",
        "verification_status": "VERIFIED",
    }
    index.add_claim(c1)

    matching_ids = index.find_supporting_claims("Developed backend service using FastAPI")
    assert "c1" in matching_ids
