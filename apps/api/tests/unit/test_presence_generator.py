"""
Unit tests for CareerOS Phase 15 — Presence Content Generator.
"""

from apps.api.app.domain.memory.models import CareerMemoryRecord
from apps.api.app.domain.presence.generator import PresenceContentGenerator


def test_generator_synthesizes_ideas_from_memories():
    user_id = "00000000-0000-0000-0000-000000000001"
    profile_id = "prof-1"

    memories = [
        CareerMemoryRecord(
            user_id=user_id,
            profile_id=profile_id,
            category="PROJECT",
            key="pgvector_search",
            content="Built hybrid vector search engine with sub-100ms latency.",
            provenance="Verified Git commit hash abc1234",
            confidence=0.95,
            verification_status="USER_CONFIRMED",
        ),
        CareerMemoryRecord(
            user_id=user_id,
            profile_id=profile_id,
            category="SKILL",
            key="fastapi_async",
            content="Asynchronous API design with Pydantic v2.",
            provenance="Verified repo production release",
            confidence=0.9,
            verification_status="EVIDENCE_VALIDATED",
        ),
    ]

    ideas = PresenceContentGenerator.generate_ideas(user_id, profile_id, memories)
    assert len(ideas) == 2
    assert any(i.content_type == "PROJECT_SHOWCASE" for i in ideas)
    assert any(i.content_type == "TECH_LEARNING" for i in ideas)


def test_generator_drafts_grounded_post():
    user_id = "00000000-0000-0000-0000-000000000001"
    profile_id = "prof-1"

    memory = CareerMemoryRecord(
        user_id=user_id,
        profile_id=profile_id,
        category="PROJECT",
        key="pgvector_search",
        content="Built hybrid vector search engine with sub-100ms latency.",
        provenance="Verified Git commit hash abc1234",
        confidence=0.95,
        verification_status="USER_CONFIRMED",
    )

    post = PresenceContentGenerator.draft_post_from_memory(
        user_id=user_id,
        profile_id=profile_id,
        memory=memory,
    )

    assert post.validation_status == "DRAFT"
    assert post.publication_mode == "USER_HANDOFF"
    assert str(memory.id) in post.grounding_evidence_ids
    assert memory.key in post.title
    assert post.quality_score >= 60.0
