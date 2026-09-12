"""
Tests for CareerOS Phase 4 Rejection Learning Loop & Skill Gap Clustering.
"""

import pytest
from uuid import UUID, uuid4
from apps.api.app.domain.learning.models import CareerOutcome
from apps.api.app.services.event_orchestrator import CareerEventOrchestrator
from apps.api.app.services.learning.service import LearningService
from apps.api.app.services.memory.service import MemoryService


@pytest.mark.asyncio
async def test_rejection_learning_gap_clustering():
    user_id = uuid4()
    profile_id = str(uuid4())
    job_id = uuid4()

    learning_service = LearningService()
    mem_service = MemoryService()
    evt_orch = CareerEventOrchestrator(memory_service=mem_service, learning_service=learning_service)

    # 1. Trigger rejection through event orchestrator
    res = await evt_orch.on_application_rejected(
        application_id=f"app-{uuid4()}",
        profile_id=UUID(profile_id),
        user_id=user_id,
        job_id=job_id,
        missing_skills=["Cloud Deployment", "System Design"],
    )

    assert res.event_type == "APPLICATION_REJECTED"
    assert res.learning_recommendations_created >= 1

    # 2. Verify Career Memory recorded RECOMMENDED_LEARNING
    memories = await mem_service.list_memories(user_id=user_id, profile_id=profile_id)
    gaps = [m for m in memories if m.category == "LEARNING_GAP"]
    assert len(gaps) >= 1
    assert any("cloud deployment" in g.key.lower() for g in gaps)
    assert gaps[0].verification_status == "RECOMMENDED_LEARNING"
