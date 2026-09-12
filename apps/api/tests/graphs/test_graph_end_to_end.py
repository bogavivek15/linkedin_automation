"""
CareerOS Phase 9.x — Complete Deterministic End-to-End Workflow Test.

Scenario:
3 Mock Jobs:
- Job A: High match, high trust, low risk -> AUTO_APPLY (ACTION_READY)
- Job B: Medium match, high trust, low risk -> USER_APPROVAL (Pauses -> Approved -> ACTION_READY)
- Job C: Low match / high risk -> REJECT (ACTION_BLOCKED)
"""

from uuid import uuid4

import pytest
from apps.api.app.domain.graph.models import RunStatus
from apps.api.app.domain.job.models import CanonicalJob
from apps.api.app.graphs.career_graph import CareerGraphRunner
from apps.api.app.graphs.dependencies import CareerGraphDependencies
from apps.api.app.repositories.approval_repository import ApprovalRepository
from apps.api.app.repositories.event_repository import EventRepository
from apps.api.app.repositories.run_repository import RunRepository
from apps.api.tests.graphs.mocks import (
    MockDecisionService,
    MockJobService,
    MockMatchService,
    MockTrustService,
)
from langgraph.checkpoint.memory import MemorySaver


@pytest.fixture(autouse=True)
def reset_stores():
    RunRepository.reset_store()
    EventRepository.reset_store()
    ApprovalRepository.reset_store()


@pytest.mark.asyncio
async def test_end_to_end_deterministic_career_graph():
    user_id = str(uuid4())
    profile_id = str(uuid4())
    run_id = str(uuid4())
    req_id = "e2e-req-001"

    job_a_id = uuid4()
    job_b_id = uuid4()
    job_c_id = uuid4()

    job_a = CanonicalJob(
        id=job_a_id,
        external_id="ext-a",
        source="TEST",
        source_url="https://example.com/a",
        title="Job A - Senior Staff AI",
        normalized_title="job a - senior staff ai",
        company_name="Anthropic",
        normalized_company="anthropic",
        description="Senior AI Engineer building systems",
        description_hash="hash-a",
    )
    job_b = CanonicalJob(
        id=job_b_id,
        external_id="ext-b",
        source="TEST",
        source_url="https://example.com/b",
        title="Job B - Full Stack Intern",
        normalized_title="job b - full stack intern",
        company_name="StartupX",
        normalized_company="startupx",
        description="Full Stack intern building React and FastAPI",
        description_hash="hash-b",
    )
    job_c = CanonicalJob(
        id=job_c_id,
        external_id="ext-c",
        source="TEST",
        source_url="https://example.com/c",
        title="Job C - Sus Scam Role",
        normalized_title="job c - sus scam role",
        company_name="UnknownScamCorp",
        normalized_company="unknownscamcorp",
        description="Pay upfront for kit",
        description_hash="hash-c",
    )

    # Mocks
    job_service = MockJobService(predefined_jobs=[job_a, job_b, job_c])
    trust_service = MockTrustService()
    trust_service.set_override(str(job_a_id), score=96.0, risk="LOW")
    trust_service.set_override(str(job_b_id), score=88.0, risk="LOW")
    trust_service.set_override(str(job_c_id), score=20.0, risk="HIGH")

    match_service = MockMatchService()
    match_service.set_override(str(job_a_id), score=94.0)
    match_service.set_override(str(job_b_id), score=82.0)
    match_service.set_override(str(job_c_id), score=35.0)

    decision_service = MockDecisionService()
    decision_service.set_action(str(job_a_id), "AUTO_APPLY")
    decision_service.set_action(str(job_b_id), "USER_APPROVAL")
    decision_service.set_action(str(job_c_id), "REJECT")

    checkpointer = MemorySaver()
    deps = CareerGraphDependencies(
        job_service=job_service,
        trust_service=trust_service,
        match_service=match_service,
        decision_service=decision_service,
        run_repository=RunRepository,
        event_repository=EventRepository,
        approval_repository=ApprovalRepository,
    )

    # 1. Execute initial run -> Should pause at approval_gate because Job B requires USER_APPROVAL
    _state1 = await CareerGraphRunner.start_run(
        run_id=run_id,
        profile_id=profile_id,
        user_id=user_id,
        request_id=req_id,
        target_roles=["AI Engineer"],
        dependencies=deps,
        checkpointer=checkpointer,
    )

    # Verify run is paused waiting for approval
    run_record = await RunRepository.get_run(uuid4() if False else uuid4().__class__(run_id), uuid4().__class__(user_id))
    assert run_record is not None
    assert run_record.status == RunStatus.WAITING_FOR_APPROVAL.value

    # Verify an approval request was created for Job B
    pending_approvals = await ApprovalRepository.get_pending_for_run(run_record.id, run_record.user_id)
    assert len(pending_approvals) == 1
    approval_b = pending_approvals[0]
    assert str(approval_b.job_id) == str(job_b_id)

    # 2. Simulate human operator approving Job B
    await ApprovalRepository.update_approval_status(
        approval_id=approval_b.id,
        user_id=run_record.user_id,
        status="APPROVED",
        resolved_by=run_record.user_id,
    )

    resume_payload = {
        "approval_id": str(approval_b.id),
        "job_id": str(job_b_id),
        "status": "APPROVED",
        "resolved_by": user_id,
    }

    # 3. Resume the workflow execution
    state2 = await CareerGraphRunner.resume_run(
        run_id=run_id,
        user_id=user_id,
        resume_payload=resume_payload,
        dependencies=deps,
        checkpointer=checkpointer,
    )

    # 4. Verify Final State
    run_final = await RunRepository.get_run(run_record.id, run_record.user_id)
    assert run_final.status == RunStatus.COMPLETED.value
    assert run_final.current_stage == "FINALIZE"
    assert run_final.completed_at is not None

    # Verify action outcomes:
    # Job A: AUTO_APPLY -> ACTION_READY
    # Job B: USER_APPROVAL -> APPROVED -> ACTION_READY
    # Job C: REJECT -> Rejected
    action_ready_job_ids = [item["job_id"] for item in state2["action_ready_jobs"]]
    assert str(job_a_id) in action_ready_job_ids
    assert str(job_b_id) in action_ready_job_ids
    assert str(job_c_id) not in action_ready_job_ids

    rejected_job_ids = [item["job_id"] for item in state2["rejected_jobs"]]
    assert str(job_c_id) in rejected_job_ids

    # 5. Verify Event Progression
    events = await EventRepository.get_events_for_run(run_id, run_record.user_id)
    event_types = [e.event_type for e in events]

    assert "RUN_STARTED" in event_types
    assert "JOB_DISCOVERY_STARTED" in event_types
    assert "JOB_DISCOVERY_COMPLETED" in event_types
    assert "TRUST_ASSESSMENT_STARTED" in event_types
    assert "TRUST_ASSESSMENT_COMPLETED" in event_types
    assert "MATCH_STARTED" in event_types
    assert "MATCH_COMPLETED" in event_types
    assert "DECISION_STARTED" in event_types
    assert "DECISION_COMPLETED" in event_types
    assert "APPROVAL_REQUIRED" in event_types
    assert "APPROVAL_APPROVED" in event_types
    assert "ACTION_READY" in event_types
    assert "ACTION_BLOCKED" in event_types
    assert "RUN_COMPLETED" in event_types
