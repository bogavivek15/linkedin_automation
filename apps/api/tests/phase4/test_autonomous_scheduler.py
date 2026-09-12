"""
Unit and integration tests for CareerOS Phase 4 Autonomous Scheduler & Concurrency Guard.
"""

import pytest
from uuid import uuid4
from apps.api.app.core.errors import CareerOSError
from apps.api.app.domain.graph.models import RunStatus
from apps.api.app.repositories.profile_repository import ProfileRepository
from apps.api.app.repositories.run_repository import RunRepository
from apps.api.app.services.scheduler.service import AutonomousOperatingScheduler


@pytest.mark.asyncio
async def test_scheduler_lifecycle_and_status():
    scheduler = AutonomousOperatingScheduler()
    status = scheduler.get_scheduler_status()
    assert "is_running" in status
    assert "configured_users_count" in status
    assert "scheduled_jobs" in status

    scheduler.start()
    assert scheduler.scheduler.running is True

    user_id = uuid4()
    scheduler.register_user_for_schedule(user_id)
    assert str(user_id) in scheduler._configured_users

    scheduler.unregister_user(user_id)
    assert str(user_id) not in scheduler._configured_users

    scheduler.shutdown(wait=False)
    import asyncio
    await asyncio.sleep(0.05)
    assert scheduler.scheduler.running is False


@pytest.mark.asyncio
async def test_scheduler_prevents_concurrent_duplicate_runs():
    scheduler = AutonomousOperatingScheduler()
    user_id = uuid4()
    u_str = str(user_id)

    # Manually mark user as currently running
    scheduler._running_users.add(u_str)

    with pytest.raises(CareerOSError) as exc_info:
        await scheduler.trigger_user_loop(user_id=user_id)

    assert exc_info.value.code == "CONCURRENT_RUN_BLOCKED"
    assert exc_info.value.status_code == 409

    # Clean up
    scheduler._running_users.discard(u_str)


@pytest.mark.asyncio
async def test_scheduler_trigger_user_loop_executes_and_persists_run():
    scheduler = AutonomousOperatingScheduler()
    user_id = uuid4()
    profile_id = uuid4()

    await ProfileRepository.save_profile(
        profile_id=profile_id,
        user_id=user_id,
        full_name="Alex Test",
        headline="AI Engineer",
    )

    summary = await scheduler.trigger_user_loop(
        user_id=user_id,
        profile_id=profile_id,
        approval_mode="MANUAL",
        limit_discovery=2,
    )

    assert summary.run_id is not None
    assert summary.completed_at is not None
    assert "Daily Career Run completed" in summary.concise_summary

    # Verify CareerRun record persisted in RunRepository
    runs = await RunRepository.list_runs_for_user(user_id)
    assert len(runs) >= 1
    latest_run = runs[0]
    assert latest_run.status == RunStatus.COMPLETED.value
    assert latest_run.profile_id == profile_id
