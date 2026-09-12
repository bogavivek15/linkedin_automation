"""
CareerOS Phase 9.x — Graph Security & User Isolation Tests.
"""

from uuid import uuid4

import pytest
from apps.api.app.domain.graph.models import ApprovalRequest, CareerRun
from apps.api.app.repositories.approval_repository import ApprovalRepository
from apps.api.app.repositories.event_repository import EventRepository
from apps.api.app.repositories.run_repository import RunRepository


@pytest.fixture(autouse=True)
def reset_stores():
    RunRepository.reset_store()
    EventRepository.reset_store()
    ApprovalRepository.reset_store()


@pytest.mark.asyncio
async def test_user_cannot_access_other_users_run():
    user_a = uuid4()
    user_b = uuid4()
    profile_a = uuid4()

    run = CareerRun(
        id=uuid4(),
        profile_id=profile_a,
        user_id=user_a,
        request_id="req-a",
        status="RUNNING",
    )
    await RunRepository.save_run(run, user_a)

    # User A can access
    found_a = await RunRepository.get_run(run.id, user_a)
    assert found_a is not None

    # User B cannot access
    found_b = await RunRepository.get_run(run.id, user_b)
    assert found_b is None


@pytest.mark.asyncio
async def test_user_cannot_access_other_users_approval():
    user_a = uuid4()
    user_b = uuid4()

    app_req = ApprovalRequest(
        id=uuid4(),
        run_id=uuid4(),
        profile_id=uuid4(),
        job_id=uuid4(),
        user_id=user_a,
        status="PENDING",
        reason="Test approval",
    )
    saved = await ApprovalRepository.save_approval(app_req, user_a)

    # User B cannot get or update
    assert await ApprovalRepository.get_approval(saved.id, user_b) is None
    assert await ApprovalRepository.update_approval_status(saved.id, user_b, "APPROVED", user_b) is None


@pytest.mark.asyncio
async def test_user_cannot_view_other_users_events():
    user_a = uuid4()
    user_b = uuid4()
    run_id = str(uuid4())

    from apps.api.app.domain.graph.models import AgentEvent
    event = AgentEvent(
        run_id=run_id,
        profile_id=str(uuid4()),
        user_id=str(user_a),
        event_type="RUN_STARTED",
        agent_name="Test",
        stage="INIT",
        status="SUCCESS",
    )
    await EventRepository.save_event(event, user_a)

    # User A sees it
    events_a = await EventRepository.get_events_for_run(run_id, user_a)
    assert len(events_a) == 1

    # User B sees nothing
    events_b = await EventRepository.get_events_for_run(run_id, user_b)
    assert len(events_b) == 0
