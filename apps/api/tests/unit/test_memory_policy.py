"""
Unit tests for CareerOS Phase 14 — Memory Write Policy & Verification Invariants.
"""

import pytest
from apps.api.app.domain.memory.policy import (
    DirectAuthoritativeMemoryWriteError,
    MemoryWritePolicy,
)


def test_ai_cannot_write_authoritative_memory():
    """
    Automated agents (actor != 'USER') are strictly prohibited from directly writing AUTHORITATIVE facts.
    """
    with pytest.raises(DirectAuthoritativeMemoryWriteError):
        MemoryWritePolicy.validate_memory_write(
            category="EXPERIENCE",
            key="senior_architect_role",
            content="5 years of principal architect experience",
            proposed_status="AUTHORITATIVE",
            actor="AI_AGENT",
            evidence_provided=False,
        )


def test_ai_without_evidence_is_proposed():
    """
    AI writing without verified evidence defaults to AI_PROPOSED status.
    """
    status = MemoryWritePolicy.validate_memory_write(
        category="SKILL",
        key="rust_systems",
        content="Proficient in Rust async programming",
        proposed_status="AI_PROPOSED",
        actor="AI_AGENT",
        evidence_provided=False,
    )
    assert status == "AI_PROPOSED"


def test_ai_with_evidence_is_evidence_validated():
    """
    AI proposing memory backed by verified evidence becomes EVIDENCE_VALIDATED.
    """
    status = MemoryWritePolicy.validate_memory_write(
        category="PROJECT",
        key="database_engine",
        content="Built a custom B-tree storage engine in C++",
        proposed_status="AI_PROPOSED",
        actor="AI_AGENT",
        evidence_provided=True,
    )
    assert status == "EVIDENCE_VALIDATED"


def test_user_can_confirm_or_write_authoritative():
    """
    Human candidate can authoritatively state or confirm memory items.
    """
    status = MemoryWritePolicy.validate_memory_write(
        category="EDUCATION",
        key="degree_bachelor",
        content="B.S. in Computer Science",
        proposed_status="AUTHORITATIVE",
        actor="USER",
    )
    assert status == "AUTHORITATIVE"
