"""
Tests for CareerOS Phase 4 Career Operating State Service.
Verifies answering:
1. WHAT IS HAPPENING?
2. WHAT NEEDS ME?
3. WHAT SHOULD I DO NEXT?
"""

import pytest
from uuid import uuid4
from apps.api.app.repositories.approval_repository import ApprovalRepository
from apps.api.app.repositories.lifecycle_repository import LifecycleRepository
from apps.api.app.repositories.profile_repository import ProfileRepository
from apps.api.app.services.memory.service import MemoryService
from apps.api.app.services.operating_state import CareerOperatingStateService


@pytest.mark.asyncio
async def test_operating_state_three_questions():
    user_id = uuid4()
    profile_id = uuid4()

    await ProfileRepository.save_profile(
        profile_id=profile_id,
        user_id=user_id,
        full_name="Jordan State",
        headline="Full Stack AI",
    )

    mem_service = MemoryService()
    await mem_service.record_memory(
        user_id=user_id,
        profile_id=str(profile_id),
        category="LEARNING_GAP",
        key="learning_gap:docker",
        content="Evidence Docker to boost interview progression.",
        provenance="Test Suite",
        proposed_status="RECOMMENDED_LEARNING",
    )

    state_service = CareerOperatingStateService(memory_service=mem_service)
    state = await state_service.get_operating_state(user_id)

    # 1. WHAT IS HAPPENING?
    assert state.what_is_happening is not None
    assert state.what_is_happening.headline is not None
    assert state.what_is_happening.active_stage in ("IDLE", "INIT", "DISCOVERY", "MATCH", "DECISION", "APPROVAL", "FINALIZE")

    # 2. WHAT NEEDS ME?
    assert state.what_needs_me is not None
    assert state.what_needs_me.unconfirmed_skills_count >= 1

    # 3. WHAT SHOULD I DO NEXT?
    assert state.what_should_i_do_next is not None
    assert len(state.what_should_i_do_next.recommendations) >= 1
    top_rec = state.what_should_i_do_next.recommendations[0]
    assert top_rec.action_type in ("EVIDENCE_GAP", "INTERVIEW_PREP", "CONNECT")
