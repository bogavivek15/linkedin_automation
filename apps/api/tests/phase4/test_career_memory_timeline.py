"""
Tests for CareerOS Phase 4 Career Memory Timeline Service.
"""

import pytest
from uuid import uuid4
from apps.api.app.services.memory.service import MemoryService
from apps.api.app.services.memory.timeline import CareerMemoryTimelineService


@pytest.mark.asyncio
async def test_career_memory_timeline_ordering_and_provenance():
    user_id = uuid4()
    profile_id = str(uuid4())
    mem_service = MemoryService()

    # 1. Verified Skill
    await mem_service.record_memory(
        user_id=user_id,
        profile_id=profile_id,
        category="SKILL",
        key="skill:python",
        content="Verified Python proficiency.",
        provenance="Transcript verification",
        proposed_status="AUTHORITATIVE",
        actor="USER",
        evidence_provided=True,
    )

    # 2. Candidate Confirmed Skill
    await mem_service.record_memory(
        user_id=user_id,
        profile_id=profile_id,
        category="SKILL",
        key="skill:docker",
        content="Verified Docker proficiency.",
        provenance="USER_CONFIRMED: Coursework certificate",
        proposed_status="USER_CONFIRMED",
        actor="USER",
        evidence_provided=True,
    )

    # 3. Learning Gap
    await mem_service.record_memory(
        user_id=user_id,
        profile_id=profile_id,
        category="LEARNING_GAP",
        key="learning_gap:kubernetes",
        content="Kubernetes cited across multiple closed applications.",
        provenance="Learning Agent",
        proposed_status="RECOMMENDED_LEARNING",
    )

    timeline_service = CareerMemoryTimelineService(memory_service=mem_service)
    entries = await timeline_service.get_timeline(user_id=user_id, profile_id=profile_id)

    assert len(entries) >= 3
    # Check that formatted dates exist
    for e in entries:
        assert e.formatted_date is not None
        assert e.badge_type in ("VERIFIED", "USER_CONFIRMED", "LEARNING_GAP", "PROJECT", "MILESTONE", "APPLICATION")

    # Badges correctly mapped
    badges = [e.badge_type for e in entries]
    assert "USER_CONFIRMED" in badges
    assert "LEARNING_GAP" in badges
