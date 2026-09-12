"""
CareerOS Phase 9.x — Graph Idempotency Tests.
"""

from uuid import uuid4

import pytest
from apps.api.app.domain.graph.models import ApprovalRequest, CareerRun
from apps.api.app.repositories.approval_repository import ApprovalRepository
from apps.api.app.repositories.run_repository import RunRepository


@pytest.fixture(autouse=True)
def reset_stores():
    RunRepository.reset_store()
    ApprovalRepository.reset_store()


@pytest.mark.asyncio
async def test_run_idempotency_by_request_id():
    user_id = uuid4()
    profile_id = uuid4()
    request_id = "idem-req-999"

    run1 = CareerRun(
        id=uuid4(),
        profile_id=profile_id,
        user_id=user_id,
        request_id=request_id,
        status="RUNNING",
    )
    await RunRepository.save_run(run1, user_id)

    # Attempting to find by request_id returns existing run
    found = await RunRepository.find_by_request_id(request_id, user_id)
    assert found is not None
    assert found.id == run1.id

    # Another user with same request_id cannot access it
    other_user = uuid4()
    found_other = await RunRepository.find_by_request_id(request_id, other_user)
    assert found_other is None


@pytest.mark.asyncio
async def test_approval_idempotency_upsert():
    user_id = uuid4()
    run_id = uuid4()
    job_id = uuid4()
    profile_id = uuid4()

    req1 = ApprovalRequest(
        id=uuid4(),
        run_id=run_id,
        profile_id=profile_id,
        job_id=job_id,
        user_id=user_id,
        status="PENDING",
        reason="First reason",
    )
    saved1 = await ApprovalRepository.save_approval(req1, user_id)

    # Creating another approval for the same run and job should update the existing record
    req2 = ApprovalRequest(
        id=uuid4(),
        run_id=run_id,
        profile_id=profile_id,
        job_id=job_id,
        user_id=user_id,
        status="PENDING",
        reason="Updated reason",
    )
    saved2 = await ApprovalRepository.save_approval(req2, user_id)

    assert saved2.id == saved1.id

    all_apps = await ApprovalRepository.list_approvals_for_user(user_id)
    assert len(all_apps) == 1
    assert all_apps[0].id == saved1.id
