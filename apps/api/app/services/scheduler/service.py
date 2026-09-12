"""
CareerOS Phase 4 — Autonomous Operating Loop Scheduler.

Production-grade background scheduling using APScheduler AsyncIOScheduler.
Coordinates periodic and on-demand execution of the 13-step DailyCareerOperatingLoop.

Key Invariants:
1. Concurrency Guard: Prevents duplicate concurrent runs for the same user.
2. Idempotency: Each run correlates to a unique CareerRun with full lifecycle audit.
3. Policy Compliance: Never bypasses configured approval gates (MANUAL, HYBRID, AUTOMATIC).
4. Failure Recovery: Provider outages or transient matching failures are isolated.
"""

import asyncio
from datetime import datetime, timezone
import logging
from typing import Any
from uuid import UUID, uuid4

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from apps.api.app.core.errors import CareerOSError
from apps.api.app.repositories.profile_repository import ProfileRepository
from apps.api.app.services.daily_operating_loop import (
    DailyCareerOperatingLoop,
    DailyOperatingRunSummary,
)

logger = logging.getLogger("careeros.scheduler")


class AutonomousOperatingScheduler:
    """
    Manages autonomous scheduled execution of CareerOS operating cycles.
    """

    _instance: "AutonomousOperatingScheduler | None" = None

    def __init__(self) -> None:
        self.scheduler = AsyncIOScheduler()
        self._user_locks: dict[str, asyncio.Lock] = {}
        self._running_users: set[str] = set()
        self._loop_engine = DailyCareerOperatingLoop()
        self._configured_users: set[str] = set()

    @classmethod
    def get_instance(cls) -> "AutonomousOperatingScheduler":
        if cls._instance is None:
            cls._instance = AutonomousOperatingScheduler()
        return cls._instance

    def _get_user_lock(self, user_id: str) -> asyncio.Lock:
        if user_id not in self._user_locks:
            self._user_locks[user_id] = asyncio.Lock()
        return self._user_locks[user_id]

    def start(self) -> None:
        """Start the background scheduler if not already running."""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("AutonomousOperatingScheduler started successfully.")

    def shutdown(self, wait: bool = False) -> None:
        """Gracefully terminate background scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=wait)
            logger.info("AutonomousOperatingScheduler shut down.")

    def configure_daily_schedule(self, hour: int = 8, minute: int = 0) -> None:
        """
        Configure recurring daily cron job for all registered users.
        """
        trigger = CronTrigger(hour=hour, minute=minute, timezone="UTC")
        self.scheduler.add_job(
            self._run_all_configured_users,
            trigger=trigger,
            id="daily_operating_loop_all_users",
            name="Daily CareerOS Autonomous Cycle",
            replace_existing=True,
        )
        logger.info("Scheduled recurring daily career cycle for %02d:%02d UTC", hour, minute)

    def register_user_for_schedule(self, user_id: UUID) -> None:
        """Register a user for recurring scheduled operating cycles."""
        self._configured_users.add(str(user_id))

    def unregister_user(self, user_id: UUID) -> None:
        """Remove user from recurring schedule."""
        self._configured_users.discard(str(user_id))

    async def _run_all_configured_users(self) -> None:
        """Execute loop across all configured users."""
        for u_str in list(self._configured_users):
            try:
                await self.trigger_user_loop(user_id=UUID(u_str))
            except Exception as e:
                logger.error("Periodic loop failed for user %s: %s", u_str, str(e))

    async def trigger_user_loop(
        self,
        user_id: UUID,
        profile_id: UUID | None = None,
        approval_mode: str = "HYBRID",
        limit_discovery: int = 10,
    ) -> DailyOperatingRunSummary:
        """
        Safely execute the autonomous career loop for a specific candidate.
        Enforces per-user concurrency lock and prevents duplicate concurrent runs.
        """
        u_str = str(user_id)

        # 1. Concurrency Check
        if u_str in self._running_users:
            raise CareerOSError(
                code="CONCURRENT_RUN_BLOCKED",
                message=f"A career operating run is already actively running for user '{user_id}'. Duplicate runs prevented.",
                status_code=409,
            )

        lock = self._get_user_lock(u_str)
        async with lock:
            self._running_users.add(u_str)
            try:
                # 2. Resolve Profile ID
                p_uuid = profile_id
                if not p_uuid:
                    prof_doc = await ProfileRepository.get_profile_by_user_id(user_id)
                    if prof_doc:
                        p_uuid = prof_doc["id"]
                    else:
                        # Fallback or initialize profile
                        p_uuid = UUID(f"00000000-0000-0000-0000-{user_id.hex[:12]}")
                        await ProfileRepository.save_profile(
                            profile_id=p_uuid,
                            user_id=user_id,
                            full_name="Candidate",
                            headline="AI & Software Engineer",
                        )

                # 3. Execute 13-step operating cycle
                summary = await self._loop_engine.execute_daily_cycle(
                    user_id=user_id,
                    profile_id=p_uuid,
                    limit_discovery=limit_discovery,
                    approval_mode=approval_mode,
                )
                return summary

            finally:
                self._running_users.discard(u_str)

    def get_scheduler_status(self) -> dict[str, Any]:
        """Inspect live scheduler state, scheduled jobs, and next run times."""
        jobs_info = []
        for job in self.scheduler.get_jobs():
            next_run = job.next_run_time.isoformat() if job.next_run_time else None
            jobs_info.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": next_run,
            })

        return {
            "is_running": self.scheduler.running,
            "configured_users_count": len(self._configured_users),
            "active_running_users": list(self._running_users),
            "scheduled_jobs": jobs_info,
            "server_time_utc": datetime.now(timezone.utc).isoformat(),
        }
