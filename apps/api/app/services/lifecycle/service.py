"""
CareerOS Phase 12 — Application Lifecycle & Communication Intelligence Service.

Coordinates persistent lifecycle state machines, auditable transitions with evidence,
and human-in-the-loop follow-up recommendations.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from apps.api.app.core.errors import CareerOSError
from apps.api.app.domain.application_lifecycle.follow_up import FollowUpIntelligenceEngine
from apps.api.app.domain.application_lifecycle.models import (
    FollowUpRecommendation,
    LifecycleEvidenceType,
    LifecycleRecord,
    LifecycleStatus,
    StatusTransition,
)
from apps.api.app.domain.application_lifecycle.interview import InterviewIntelligenceEngine
from apps.api.app.domain.application_lifecycle.policy import LifecyclePolicy
from apps.api.app.repositories.job_repository import JobRepository
from apps.api.app.repositories.lifecycle_repository import LifecycleRepository
from apps.api.app.repositories.profile_repository import ProfileRepository


class LifecycleService:
    """
    Coordinates application lifecycle transitions and follow-up communications.
    """

    async def get_or_create_lifecycle(
        self,
        application_id: UUID | str,
        user_id: UUID,
        job_id: UUID | str,
        initial_status: LifecycleStatus = "PREPARED",
    ) -> LifecycleRecord:
        """
        Get or initialize lifecycle tracking for an application.
        """
        existing = await LifecycleRepository.get_by_application_id(application_id, user_id)
        if existing:
            return existing

        now = datetime.now(timezone.utc)
        record = LifecycleRecord(
            id=str(uuid4()),
            application_id=str(application_id),
            user_id=str(user_id),
            job_id=str(job_id),
            current_status=initial_status,
            last_transition_at=now,
            created_at=now,
            updated_at=now,
        )
        saved = await LifecycleRepository.save_lifecycle(record, user_id)

        # Record initial transition
        trans = StatusTransition(
            id=str(uuid4()),
            lifecycle_id=saved.id,
            user_id=str(user_id),
            from_status="DISCOVERED" if initial_status != "DISCOVERED" else "DISCOVERED",
            to_status=initial_status,
            evidence_type="MANUALLY_ENTERED",
            actor="SYSTEM",
            notes="Lifecycle tracking initialized",
            created_at=now,
        )
        await LifecycleRepository.add_transition(trans, user_id)
        saved.transitions = [trans]
        return saved

    async def transition_status(
        self,
        lifecycle_id: UUID | str,
        user_id: UUID,
        to_status: LifecycleStatus,
        evidence_type: LifecycleEvidenceType,
        evidence_details: dict[str, Any] | None = None,
        notes: str | None = None,
        actor: str = "USER",
    ) -> tuple[LifecycleRecord, StatusTransition]:
        """
        Execute an auditable state transition with evidence validation.
        """
        lifecycle = await LifecycleRepository.get_lifecycle(lifecycle_id, user_id)
        if not lifecycle:
            raise CareerOSError(
                code="LIFECYCLE_NOT_FOUND",
                message=f"Lifecycle record '{lifecycle_id}' not found",
                status_code=404,
            )

        from_status = lifecycle.current_status

        # 1. Deterministic Policy Validation
        LifecyclePolicy.validate_transition(
            from_status=from_status,
            to_status=to_status,
            evidence_type=evidence_type,
            evidence_details=evidence_details,
        )

        now = datetime.now(timezone.utc)

        # 2. Record Transition Audit
        transition = StatusTransition(
            id=str(uuid4()),
            lifecycle_id=str(lifecycle.id),
            user_id=str(user_id),
            from_status=from_status,
            to_status=to_status,
            evidence_type=evidence_type,
            evidence_details=evidence_details or {},
            actor=actor,
            notes=notes,
            created_at=now,
        )
        await LifecycleRepository.add_transition(transition, user_id)

        # 3. Update Lifecycle State
        lifecycle.current_status = to_status
        lifecycle.last_transition_at = now
        lifecycle.updated_at = now
        await LifecycleRepository.save_lifecycle(lifecycle, user_id)

        # 4. Check for automated Follow-up recommendation
        job = await JobRepository.get_job_by_id(UUID(lifecycle.job_id), user_id)
        job_dict = job.model_dump(mode="json") if job else {}
        follow_up = FollowUpIntelligenceEngine.evaluate_follow_up(lifecycle, job_dict)
        if follow_up:
            await LifecycleRepository.add_follow_up(follow_up, user_id)

        # 5. CareerOS Phase 4: Interview Intelligence Trigger
        if to_status in ("ASSESSMENT", "INTERVIEW", "TECHNICAL", "HR"):
            try:
                profile_dict = await ProfileRepository.get_profile_by_user_id(user_id) or {}
                skills_list = [s.get("skill_name") for s in profile_dict.get("skills", []) if isinstance(s, dict)]
                plan = InterviewIntelligenceEngine.generate_plan(
                    lifecycle_id=str(lifecycle.id),
                    application_id=lifecycle.application_id,
                    user_id=str(user_id),
                    job_id=lifecycle.job_id,
                    company_name=job.company_name if job else "Hiring Company",
                    role_title=job.title if job else "Target Role",
                    stage=to_status,  # type: ignore
                    job_requirements=job.required_skills if job else [],
                    verified_skills=skills_list,
                    missing_skills=[],
                    project_claims=profile_dict.get("experience", []),
                )
                lifecycle.metadata["interview_prep_plan"] = plan.model_dump(mode="json")
                await LifecycleRepository.save_lifecycle(lifecycle, user_id)

                # Emit notification
                from apps.api.app.services.notifications.service import NotificationService
                await NotificationService().emit_notification(
                    user_id=user_id,
                    notification_type="INTERVIEW_UPDATE",
                    title=f"Interview Intelligence Ready: {to_status} for {job.title if job else 'Role'}",
                    message=f"CareerOS prepared a tailored {to_status} prep plan with {len(plan.recommended_topics)} topics and grounded project talking points.",
                    action_url=f"/applications/{lifecycle.application_id}",
                    metadata={"plan_id": plan.id, "stage": to_status},
                )

                # Emit event telemetry
                from apps.api.app.graphs.events import GraphEventBus
                await GraphEventBus.emit(
                    run_id=f"lc-{lifecycle.id}",
                    profile_id=str(profile_dict.get("id") or user_id),
                    user_id=str(user_id),
                    event_type="INTERVIEW_PREP_GENERATED",
                    agent_name="Interview Intelligence",
                    stage="LIFECYCLE_ASSIST",
                    metadata={"stage": to_status, "topics_count": len(plan.recommended_topics)},
                )
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning("Failed to generate interview prep plan: %s", e)

        # 6. CareerOS Phase 4: Rejection Learning Trigger
        elif to_status == "REJECTED":
            try:
                from apps.api.app.services.event_orchestrator import CareerEventOrchestrator
                from apps.api.app.services.learning.service import LearningService
                from apps.api.app.domain.learning.models import CareerOutcome

                profile_dict = await ProfileRepository.get_profile_by_user_id(user_id) or {}
                profile_id = profile_dict.get("id") or user_id

                missing_skills = job.required_skills if job else []
                # Record in LearningService
                outcome = CareerOutcome(
                    user_id=str(user_id),
                    profile_id=str(profile_id),
                    application_id=lifecycle.application_id,
                    job_id=lifecycle.job_id,
                    outcome_type="REJECTED_FINAL",
                    extracted_skill_gaps=missing_skills[:3],
                    notes=notes or "Application closed/rejected",
                )
                await LearningService().record_outcome(outcome, user_id)

                # Trigger orchestrator feedback loop
                await CareerEventOrchestrator().on_application_rejected(
                    application_id=lifecycle.application_id,
                    profile_id=profile_id,
                    user_id=user_id,
                    job_id=UUID(lifecycle.job_id),
                    missing_skills=missing_skills[:3],
                )
            except Exception:
                pass

        # Re-fetch complete lifecycle
        updated = await LifecycleRepository.get_lifecycle(lifecycle_id, user_id)
        return updated or lifecycle, transition

    async def get_lifecycle(self, lifecycle_id: UUID | str, user_id: UUID) -> LifecycleRecord | None:
        """Get lifecycle by ID."""
        return await LifecycleRepository.get_lifecycle(lifecycle_id, user_id)

    async def get_by_application_id(self, application_id: UUID | str, user_id: UUID) -> LifecycleRecord | None:
        """Get lifecycle by application ID."""
        return await LifecycleRepository.get_by_application_id(application_id, user_id)

    async def list_lifecycles(self, user_id: UUID, status: str | None = None) -> list[LifecycleRecord]:
        """List lifecycles for user."""
        return await LifecycleRepository.list_lifecycles(user_id, status)

    async def check_and_generate_follow_up(
        self,
        lifecycle_id: UUID | str,
        user_id: UUID,
    ) -> FollowUpRecommendation | None:
        """
        Manually trigger or evaluate follow-up recommendation for a lifecycle record.
        """
        lifecycle = await LifecycleRepository.get_lifecycle(lifecycle_id, user_id)
        if not lifecycle:
            return None

        job = await JobRepository.get_job_by_id(UUID(lifecycle.job_id), user_id)
        job_dict = job.model_dump(mode="json") if job else {}

        rec = FollowUpIntelligenceEngine.evaluate_follow_up(lifecycle, job_dict)
        if rec:
            await LifecycleRepository.add_follow_up(rec, user_id)
        return rec

    async def update_follow_up_status(
        self,
        lifecycle_id: UUID | str,
        follow_up_id: UUID | str,
        user_id: UUID,
        new_status: str,
        user_notes: str | None = None,
    ) -> FollowUpRecommendation:
        """
        User approval/dismissal/sent update on a follow-up draft.
        """
        follow_ups = await LifecycleRepository.get_follow_ups(lifecycle_id, user_id)
        match = next((f for f in follow_ups if f.id == str(follow_up_id)), None)
        if not match:
            raise CareerOSError(
                code="FOLLOW_UP_NOT_FOUND",
                message="Follow-up recommendation not found",
                status_code=404,
            )

        now = datetime.now(timezone.utc)
        match.status = new_status  # type: ignore
        if user_notes:
            match.user_notes = user_notes
        if new_status == "SENT":
            match.sent_at = now
        match.updated_at = now

        await LifecycleRepository.update_follow_up(match, user_id)
        return match
