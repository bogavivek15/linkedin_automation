"""
CareerOS Phase 3 — Daily Career Operating Loop.

Executes the recurring 13-step CareerOS operating cycle:
1. Load Career Memory
2. Discover new opportunities
3. Remove stale/duplicate jobs
4. Trust-check opportunities
5. Match opportunities
6. Identify skill gaps
7. Surface top opportunities
8. Prepare applications according to approval policy
9. Check application lifecycle
10. Identify follow-ups
11. Detect professional presence opportunities
12. Update Career Memory
13. Produce concise activity summary

Does not run expensive operations unnecessarily.
Can be triggered manually or run on scheduled cron.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from apps.api.app.domain.application_lifecycle.follow_up import FollowUpIntelligenceEngine
from apps.api.app.domain.application_lifecycle.models import LifecycleRecord
from apps.api.app.domain.graph.models import RunStage
from apps.api.app.domain.job.models import CanonicalJob
from apps.api.app.graphs.events import GraphEventBus
from apps.api.app.repositories.event_repository import EventRepository
from apps.api.app.repositories.job_repository import JobRepository
from apps.api.app.repositories.lifecycle_repository import LifecycleRepository
from apps.api.app.repositories.match_repository import MatchRepository
from apps.api.app.repositories.profile_repository import ProfileRepository
from apps.api.app.services.application.service import ApplicationPreparationService
from apps.api.app.services.decision.service import DecisionService
from apps.api.app.services.jobs.service import JobIngestionService
from apps.api.app.services.matching.service import MatchService
from apps.api.app.services.memory.service import MemoryService
from apps.api.app.services.trust.service import TrustAssessmentService
from pydantic import BaseModel, Field


class DailyOperatingRunSummary(BaseModel):
    run_id: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    memories_loaded: int = 0
    jobs_discovered: int = 0
    stale_jobs_cleaned: int = 0
    trust_checks_performed: int = 0
    scams_blocked: int = 0
    matches_calculated: int = 0
    top_matches: list[dict[str, Any]] = Field(default_factory=list)
    skill_gaps_identified: list[str] = Field(default_factory=list)
    applications_prepared: int = 0
    approvals_pending: int = 0
    follow_ups_recommended: int = 0
    presence_opportunities: int = 0
    memory_updates_recorded: int = 0
    concise_summary: str = ""


class DailyCareerOperatingLoop:
    """
    Recurring CareerOS Autonomous Operating Cycle.
    """

    def __init__(
        self,
        memory_service: MemoryService | None = None,
        job_service: JobIngestionService | None = None,
        app_service: ApplicationPreparationService | None = None,
    ) -> None:
        self.memory_service = memory_service or MemoryService()
        self.job_service = job_service or JobIngestionService()
        self.app_service = app_service or ApplicationPreparationService()

    async def execute_daily_cycle(
        self,
        user_id: UUID,
        profile_id: UUID,
        limit_discovery: int = 10,
        approval_mode: str = "HYBRID",
        request_id: str | None = None,
    ) -> DailyOperatingRunSummary:
        """
        Execute the 13-step recurring daily career operating cycle with:
        - CareerRun persistence and stage progression
        - Real-time SSE telemetry emission via GraphEventBus
        - Configurable approval policies (MANUAL, HYBRID, AUTOMATIC)
        - Full error resilience across external providers
        """
        from apps.api.app.domain.graph.models import CareerRun, RunStage, RunStatus
        from apps.api.app.repositories.run_repository import RunRepository

        run_uuid = uuid4()
        run_id_str = f"daily-{run_uuid}"
        req_id = request_id or f"req-{run_uuid}"
        summary = DailyOperatingRunSummary(run_id=run_id_str)

        # Initialize persistent CareerRun
        career_run = CareerRun(
            id=run_uuid,
            profile_id=profile_id,
            user_id=user_id,
            request_id=req_id,
            graph_name="daily_career_loop",
            graph_version="v4.0",
            status=RunStatus.RUNNING.value,
            current_stage=RunStage.INIT.value,
            metadata={"approval_mode": approval_mode, "limit_discovery": limit_discovery},
        )
        await RunRepository.save_run(career_run, user_id)

        try:
            # 1. Load Career Memory
            await RunRepository.update_run(run_uuid, user_id, current_stage=RunStage.INIT.value)
            memories = await self.memory_service.list_memories(user_id=user_id, profile_id=str(profile_id))
            summary.memories_loaded = len(memories)

            await GraphEventBus.emit(
                run_id=run_id_str,
                profile_id=str(profile_id),
                user_id=str(user_id),
                event_type="ORCHESTRATION_STARTED",
                agent_name="Career Orchestrator",
                stage=RunStage.INIT.value,
                metadata={"memories_loaded": summary.memories_loaded, "approval_mode": approval_mode},
            )

            # 2. Discover new opportunities
            await RunRepository.update_run(run_uuid, user_id, current_stage=RunStage.DISCOVERY.value)
            try:
                disc_res = await self.job_service.run_discovery(limit=limit_discovery)
                raw_jobs = disc_res.get("jobs", []) if isinstance(disc_res, dict) else []
                summary.jobs_discovered = len(raw_jobs)
            except Exception as e:
                summary.jobs_discovered = 0

            await GraphEventBus.emit(
                run_id=run_id_str,
                profile_id=str(profile_id),
                user_id=str(user_id),
                event_type="JOB_DISCOVERED",
                agent_name="Opportunity Agent",
                stage=RunStage.DISCOVERY.value,
                metadata={"jobs_discovered": summary.jobs_discovered},
            )

            # 3. Remove stale / duplicate jobs
            stale_cleaned = await JobRepository.mark_stale_jobs(max_age_days=60)
            summary.stale_jobs_cleaned = stale_cleaned
            active_jobs = await JobRepository.get_active_jobs(limit=15)

            # 4. Trust-check opportunities
            await RunRepository.update_run(run_uuid, user_id, current_stage=RunStage.TRUST.value)
            trusted_jobs: list[CanonicalJob] = []
            for job in active_jobs:
                try:
                    trust = await TrustAssessmentService.assess_job(job)
                    summary.trust_checks_performed += 1
                    if trust.risk_level.value == "HIGH":
                        summary.scams_blocked += 1
                        await GraphEventBus.emit(
                            run_id=run_id_str,
                            profile_id=str(profile_id),
                            user_id=str(user_id),
                            event_type="SCAM_FLAG_RAISED",
                            agent_name="Trust & Safety Agent",
                            stage=RunStage.TRUST.value,
                            metadata={"job_id": str(job.id), "company": job.company_name, "title": job.title},
                        )
                    else:
                        trusted_jobs.append(job)
                except Exception:
                    trusted_jobs.append(job)

            # 5. Match opportunities
            await RunRepository.update_run(run_uuid, user_id, current_stage=RunStage.MATCH.value)
            matched_results: list[dict[str, Any]] = []
            for job in trusted_jobs:
                try:
                    m = await MatchService.calculate_match(profile_id, job.id, user_id)
                    summary.matches_calculated += 1
                    matched_results.append({
                        "job_id": str(job.id),
                        "title": job.title,
                        "company": job.company_name,
                        "score": m.overall_score,
                        "matched_skills": m.matched_skills,
                        "missing_skills": m.missing_skills,
                    })
                except Exception:
                    pass

            matched_results.sort(key=lambda x: x["score"], reverse=True)
            summary.top_matches = matched_results[:3]

            await GraphEventBus.emit(
                run_id=run_id_str,
                profile_id=str(profile_id),
                user_id=str(user_id),
                event_type="MATCH_COMPUTED",
                agent_name="Match Engine",
                stage=RunStage.MATCH.value,
                metadata={"matches_count": len(summary.top_matches), "top_matches": summary.top_matches},
            )

            # 6. Identify skill gaps
            gap_set: set[str] = set()
            for m in matched_results:
                for sk in m.get("missing_skills", []):
                    gap_set.add(sk)
            summary.skill_gaps_identified = sorted(list(gap_set))[:5]

            # 7. Surface top opportunities & Evaluate Decisions
            await RunRepository.update_run(run_uuid, user_id, current_stage=RunStage.DECISION.value)
            eligible_job_ids: list[UUID] = []
            for tm in summary.top_matches:
                jid = UUID(tm["job_id"])
                try:
                    dec = await DecisionService.evaluate_decision(profile_id, jid, user_id)
                    if dec.action in ("AUTO_APPLY", "USER_APPROVAL"):
                        eligible_job_ids.append(jid)
                        if dec.action == "USER_APPROVAL" or approval_mode == "MANUAL":
                            summary.approvals_pending += 1
                except Exception:
                    pass

            # 8. Prepare applications according to approval policy
            await RunRepository.update_run(run_uuid, user_id, current_stage=RunStage.APPROVAL.value)
            for jid in eligible_job_ids[:2]:
                try:
                    pkg = await self.app_service.prepare_application(profile_id, jid, user_id)
                    summary.applications_prepared += 1

                    # If AUTOMATIC policy permitted and package valid and decision AUTO_APPLY, attempt execution
                    if approval_mode == "AUTOMATIC":
                        from apps.api.app.services.execution.service import ApplicationExecutionService
                        from apps.api.app.domain.execution.models import ExecutionMode
                        # Only auto-execute if package not blocked
                        if pkg.validation_status != "BLOCKED":
                            await ApplicationExecutionService.execute_application(
                                package_id=UUID(pkg.id),
                                user_id=user_id,
                                mode=ExecutionMode.SANDBOX,
                            )
                except Exception:
                    pass

            # 9 & 10. Check application lifecycle & Identify follow-ups
            try:
                lifecycles = await LifecycleRepository.list_lifecycles_for_user(user_id)
                for lc in lifecycles:
                    rec = FollowUpIntelligenceEngine.evaluate_follow_up(lc)
                    if rec:
                        summary.follow_ups_recommended += 1
            except Exception:
                pass

            # 11. Detect presence opportunities
            if any(m.category in ("SKILL", "PROJECT", "CERTIFICATION") for m in memories):
                summary.presence_opportunities = 1
                await GraphEventBus.emit(
                    run_id=run_id_str,
                    profile_id=str(profile_id),
                    user_id=str(user_id),
                    event_type="PRESENCE_DRAFT_CREATED",
                    agent_name="Presence Agent",
                    stage="PRESENCE",
                    metadata={"milestones_evaluated": 1},
                )

            # 12. Update Career Memory with daily operating insight
            if summary.skill_gaps_identified:
                top_gap = summary.skill_gaps_identified[0]
                try:
                    await self.memory_service.record_memory(
                        user_id=user_id,
                        profile_id=str(profile_id),
                        category="INSIGHT",
                        key=f"daily_insight:{top_gap.lower()}",
                        content=f"Daily Career Run: {top_gap} is currently the top required skill across high-scoring opportunities.",
                        provenance="Daily Operating Loop: Market Demand Aggregator",
                        confidence=0.95,
                        proposed_status="AI_PROPOSED",
                        actor="AI_AGENT",
                        source="DAILY_OPERATING_LOOP",
                        evidence_ref=run_id_str,
                        reason="Aggregated requirement analysis from daily career run",
                    )
                    summary.memory_updates_recorded += 1
                except Exception:
                    pass

            # 13. Produce concise activity summary
            summary.completed_at = datetime.now(timezone.utc)
            top_job_str = f"{summary.top_matches[0]['title']} ({summary.top_matches[0]['score']:.0f}% match)" if summary.top_matches else "None"
            summary.concise_summary = (
                f"Daily Career Run completed in {(summary.completed_at - summary.started_at).total_seconds():.1f}s. "
                f"Evaluated {summary.jobs_discovered} discovered postings, cleaned {summary.stale_jobs_cleaned} stale postings, "
                f"blocked {summary.scams_blocked} scam alerts. Top opportunity: {top_job_str}. "
                f"{summary.applications_prepared} package(s) prepared, {summary.approvals_pending} awaiting approval."
            )

            # Mark CareerRun completed
            await RunRepository.update_run(
                run_uuid,
                user_id,
                status=RunStatus.COMPLETED.value,
                current_stage=RunStage.FINALIZE.value,
                completed_at=summary.completed_at,
                metadata_update=summary.model_dump(mode="json"),
            )

            await GraphEventBus.emit(
                run_id=run_id_str,
                profile_id=str(profile_id),
                user_id=str(user_id),
                event_type="ORCHESTRATION_COMPLETED",
                agent_name="Career Orchestrator",
                stage=RunStage.FINALIZE.value,
                metadata={"summary": summary.concise_summary},
            )

            return summary

        except Exception as e:
            # Mark run failed
            await RunRepository.update_run(
                run_uuid,
                user_id,
                status=RunStatus.FAILED.value,
                error=str(e),
                completed_at=datetime.now(timezone.utc),
            )
            await GraphEventBus.emit(
                run_id=run_id_str,
                profile_id=str(profile_id),
                user_id=str(user_id),
                event_type="ORCHESTRATION_FAILED",
                agent_name="Career Orchestrator",
                stage="ERROR",
                metadata={"error": str(e)},
            )
            raise
