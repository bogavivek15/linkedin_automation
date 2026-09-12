"""
Orchestrator Agent: pure coordinator.

Dispatches Opportunity, Trust, Application, and Presence agents.
Never writes authoritative database records itself.
"""

from __future__ import annotations

import logging
from uuid import UUID, uuid4, uuid5, NAMESPACE_DNS

from apps.api.app.domain.application.agent import application_agent
from apps.api.app.domain.job.gemini_search import opportunity_agent
from apps.api.app.domain.trust.models import RiskLevel, TrustContext
from apps.api.app.domain.trust.policy import TrustPolicy
from apps.api.app.domain.presence.scheduler import presence_scheduler
from apps.api.app.graphs.events import GraphEventBus

logger = logging.getLogger("careeros.orchestrator")


def _as_uuid(value: str) -> UUID:
    try:
        return UUID(str(value))
    except ValueError:
        return uuid5(NAMESPACE_DNS, str(value))


class OrchestratorWorkflow:
    """Coordinates the multi-agent automation cycle."""

    def __init__(self) -> None:
        self.trust_policy = TrustPolicy()

    async def run_automation_cycle(
        self,
        user_id: str,
        profile_id: str,
        resume_context: str,
        target_roles: str,
        locations: str,
    ) -> dict:
        run_id = str(uuid4())
        logger.info("Starting orchestration cycle run_id=%s user=%s", run_id, user_id)

        await GraphEventBus.emit(
            run_id=run_id,
            profile_id=profile_id,
            user_id=user_id,
            event_type="ORCHESTRATION_STARTED",
            agent_name="Orchestrator Agent",
            stage="INIT",
            metadata={"target_roles": target_roles, "locations": locations},
        )

        await GraphEventBus.emit(
            run_id=run_id,
            profile_id=profile_id,
            user_id=user_id,
            event_type="PROFILE_UPDATED",
            agent_name="Profile Agent",
            stage="MEMORY",
            metadata={"resume_chars": len(resume_context or ""), "commit": False},
        )

        # Sub-agent 1: Opportunity
        jobs = opportunity_agent.search_jobs(target_roles, locations)
        jobs = await opportunity_agent.persist_jobs(jobs)
        await GraphEventBus.emit(
            run_id=run_id,
            profile_id=profile_id,
            user_id=user_id,
            event_type="JOB_DISCOVERED",
            agent_name="Opportunity Agent",
            stage="DISCOVERY",
            metadata={"count": len(jobs)},
        )
        await GraphEventBus.emit(
            run_id=run_id,
            profile_id=profile_id,
            user_id=user_id,
            event_type="JOB_NORMALIZED",
            agent_name="Opportunity Agent",
            stage="DISCOVERY",
            metadata={"count": len(jobs)},
        )
        await GraphEventBus.emit(
            run_id=run_id,
            profile_id=profile_id,
            user_id=user_id,
            event_type="ORCHESTRATION_STAGE_COMPLETED",
            agent_name="Orchestrator Agent",
            stage="DISCOVERY",
            metadata={"jobs": len(jobs)},
        )

        # Sub-agent 2: Trust
        await GraphEventBus.emit(
            run_id=run_id,
            profile_id=profile_id,
            user_id=user_id,
            event_type="TRUST_ASSESSMENT_STARTED",
            agent_name="Trust Agent",
            stage="TRUST",
            metadata={"total_jobs": len(jobs)},
        )

        trusted_jobs = []
        rejected = []
        assessments = []
        for job in jobs:
            context = TrustContext(
                job=job,
                company_name=job.company_name,
                company_website=(job.metadata or {}).get("company_website") or (job.metadata or {}).get("website_url"),
                application_url=job.application_url or "",
            )
            assessment = await self.trust_policy.evaluate_opportunity(context)
            assessments.append(
                {
                    "job_id": str(job.id),
                    "title": job.title,
                    "company_name": job.company_name,
                    "trust_score": assessment.trust_score,
                    "risk_level": assessment.risk_level.value,
                    "suspicious_signals": assessment.suspicious_signals,
                }
            )
            if assessment.risk_level == RiskLevel.HIGH:
                await GraphEventBus.emit(
                    run_id=run_id,
                    profile_id=profile_id,
                    user_id=user_id,
                    event_type="SCAM_FLAG_RAISED",
                    agent_name="Trust Agent",
                    stage="TRUST",
                    job_id=str(job.id),
                    metadata={"company": job.company_name, "signals": assessment.suspicious_signals},
                )
                rejected.append(job.title)
            elif self.trust_policy.is_trusted(assessment):
                trusted_jobs.append(job)

        await GraphEventBus.emit(
            run_id=run_id,
            profile_id=profile_id,
            user_id=user_id,
            event_type="TRUST_ASSESSMENT_COMPLETED",
            agent_name="Trust Agent",
            stage="TRUST",
            metadata={"trusted": len(trusted_jobs), "rejected": len(rejected)},
        )
        await GraphEventBus.emit(
            run_id=run_id,
            profile_id=profile_id,
            user_id=user_id,
            event_type="ORCHESTRATION_STAGE_COMPLETED",
            agent_name="Orchestrator Agent",
            stage="TRUST",
            metadata={"trusted_jobs": len(trusted_jobs)},
        )

        # Sub-agent 3: Application (writes packages; orchestrator does not)
        await GraphEventBus.emit(
            run_id=run_id,
            profile_id=profile_id,
            user_id=user_id,
            event_type="PACKAGE_PREPARATION_STARTED",
            agent_name="Application Agent",
            stage="APPLICATION_PREPARATION",
            metadata={"jobs": len(trusted_jobs)},
        )
        packages = await application_agent.prepare_for_trusted_jobs(
            user_id=_as_uuid(user_id),
            profile_id=profile_id,
            jobs=trusted_jobs,
            resume_context=resume_context,
        )
        await GraphEventBus.emit(
            run_id=run_id,
            profile_id=profile_id,
            user_id=user_id,
            event_type="PACKAGE_READY_FOR_REVIEW",
            agent_name="Application Agent",
            stage="APPLICATION_PREPARATION",
            metadata={"packages": len(packages)},
        )

        # Sub-agent 4: Presence — schedule daily + initial handoff draft
        presence_scheduler.schedule_daily_post(
            user_id=user_id,
            profile_id=profile_id,
            context_text=resume_context,
        )
        presence_post = await presence_scheduler.run_presence_generation(
            user_id=user_id,
            profile_id=profile_id,
            context_text=resume_context,
        )
        await GraphEventBus.emit(
            run_id=run_id,
            profile_id=profile_id,
            user_id=user_id,
            event_type="PRESENCE_DRAFT_CREATED",
            agent_name="Presence Agent",
            stage="PRESENCE_SYNTHESIS",
            metadata={"post_id": presence_post.id, "publication_mode": presence_post.publication_mode},
        )
        await GraphEventBus.emit(
            run_id=run_id,
            profile_id=profile_id,
            user_id=user_id,
            event_type="HANDOFF_READY",
            agent_name="Presence Agent",
            stage="PRESENCE_SYNTHESIS",
            metadata={"post_id": presence_post.id},
        )

        await GraphEventBus.emit(
            run_id=run_id,
            profile_id=profile_id,
            user_id=user_id,
            event_type="ORCHESTRATION_COMPLETED",
            agent_name="Orchestrator Agent",
            stage="FINALIZE",
            metadata={"trusted_jobs_count": len(trusted_jobs)},
        )

        return {
            "status": "success",
            "run_id": run_id,
            "jobs_discovered": len(jobs),
            "trusted_jobs_count": len(trusted_jobs),
            "rejected_jobs": rejected,
            "applications_prepared": len(packages),
            "presence_post_id": presence_post.id,
            "assessments": assessments,
            "trusted_jobs": [
                {
                    "id": str(job.id),
                    "title": job.title,
                    "company_name": job.company_name,
                    "location": job.location,
                    "application_url": job.application_url,
                }
                for job in trusted_jobs
            ],
        }


orchestrator = OrchestratorWorkflow()
