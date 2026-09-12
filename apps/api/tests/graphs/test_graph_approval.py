"""
CareerOS Phase 9.x — Human-in-the-Loop Approval Tests.
"""

from uuid import uuid4

import pytest
from apps.api.app.domain.graph.models import ApprovalRequest, ApprovalStatus
from apps.api.app.repositories.approval_repository import ApprovalRepository


@pytest.fixture(autouse=True)
def reset_stores():
    ApprovalRepository.reset_store()


@pytest.mark.asyncio
async def test_approval_lifecycle_approve():
    user_id = uuid4()
    run_id = uuid4()
    job_id = uuid4()
    profile_id = uuid4()

    app_req = ApprovalRequest(
        id=uuid4(),
        run_id=run_id,
        profile_id=profile_id,
        job_id=job_id,
        user_id=user_id,
        status=ApprovalStatus.PENDING.value,
        requested_action="REVIEW",
        reason="Match requires manual approval",
        job_title="Full Stack Engineer",
        company_name="Vercel",
        match_score=85.0,
        trust_score=92.0,
    )

    saved = await ApprovalRepository.save_approval(app_req, user_id)
    assert saved.status == ApprovalStatus.PENDING.value

    # Approve
    updated = await ApprovalRepository.update_approval_status(
        approval_id=saved.id,
        user_id=user_id,
        status=ApprovalStatus.APPROVED.value,
        resolved_by=user_id,
    )

    assert updated.status == ApprovalStatus.APPROVED.value
    assert updated.resolved_at is not None
    assert updated.resolved_by == user_id


@pytest.mark.asyncio
async def test_approval_lifecycle_reject():
    user_id = uuid4()
    app_req = ApprovalRequest(
        id=uuid4(),
        run_id=uuid4(),
        profile_id=uuid4(),
        job_id=uuid4(),
        user_id=user_id,
        status=ApprovalStatus.PENDING.value,
        reason="Manual review required",
    )

    saved = await ApprovalRepository.save_approval(app_req, user_id)

    # Reject
    updated = await ApprovalRepository.update_approval_status(
        approval_id=saved.id,
        user_id=user_id,
        status=ApprovalStatus.REJECTED.value,
        resolved_by=user_id,
    )

    assert updated.status == ApprovalStatus.REJECTED.value
    assert updated.resolved_at is not None
