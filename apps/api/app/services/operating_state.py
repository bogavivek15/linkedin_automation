"""
CareerOS Phase 4 — Career Operating State Engine.

Answers the three essential questions for the candidate:
1. WHAT IS HAPPENING? (Current autonomous loop state, active stages, live telemetry)
2. WHAT NEEDS ME? (Human-in-the-loop approvals, skill confirmations, sensitive checks)
3. WHAT SHOULD I DO NEXT? (Interview prep, learning gap evidence, follow-up actions)
"""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from apps.api.app.repositories.approval_repository import ApprovalRepository
from apps.api.app.repositories.event_repository import EventRepository
from apps.api.app.repositories.lifecycle_repository import LifecycleRepository
from apps.api.app.repositories.run_repository import RunRepository
from apps.api.app.services.memory.service import MemoryService
from apps.api.app.services.scheduler.service import AutonomousOperatingScheduler


class WhatIsHappeningSection(BaseModel):
    headline: str
    active_stage: str
    is_actively_running: bool
    jobs_evaluated: int = 0
    top_match_title: str | None = None
    top_match_score: float | None = None
    scams_blocked: int = 0
    active_applications_count: int = 0
    recent_agent_actions: list[str] = Field(default_factory=list)


class WhatNeedsMeSection(BaseModel):
    total_actions_required: int = 0
    pending_approvals_count: int = 0
    unconfirmed_skills_count: int = 0
    pending_follow_ups_count: int = 0
    action_items: list[dict[str, Any]] = Field(default_factory=list)


class NextActionItem(BaseModel):
    action_type: str  # INTERVIEW_PREP, EVIDENCE_GAP, REVIEW_DRAFT, CONNECT
    priority: str  # HIGH, MEDIUM, LOW
    title: str
    description: str
    target_url: str


class WhatShouldIDoNextSection(BaseModel):
    recommendations: list[NextActionItem] = Field(default_factory=list)


class OperatingStateResponse(BaseModel):
    user_id: str
    current_operating_state: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    what_is_happening: WhatIsHappeningSection
    what_needs_me: WhatNeedsMeSection
    what_should_i_do_next: WhatShouldIDoNextSection


class CareerOperatingStateService:
    """
    Computes real-time career state by aggregating runs, approvals, memory, and lifecycles.
    """

    def __init__(self, memory_service: MemoryService | None = None):
        self.memory_service = memory_service or MemoryService()

    async def get_operating_state(self, user_id: UUID) -> OperatingStateResponse:
        u_str = str(user_id)
        scheduler = AutonomousOperatingScheduler.get_instance()
        is_user_running = u_str in scheduler._running_users

        # 1. Fetch runs
        runs = await RunRepository.list_runs_for_user(user_id)
        active_run = next((r for r in runs if r.status == "RUNNING"), None)
        latest_run = runs[0] if runs else None

        # 2. Fetch pending approvals
        approvals = await ApprovalRepository.list_pending(user_id)

        # 3. Fetch lifecycles
        lifecycles = await LifecycleRepository.list_lifecycles_for_user(user_id)
        active_lifecycles = [lc for lc in lifecycles if lc.current_status not in ("REJECTED", "ARCHIVED", "WITHDRAWN")]

        # 4. Fetch memories
        memories = await self.memory_service.list_memories(user_id=user_id)
        unconfirmed = [m for m in memories if m.verification_status in ("AI_PROPOSED", "RECOMMENDED_LEARNING")]

        # 5. Fetch recent events
        recent_events = await EventRepository.get_events_for_run(
            latest_run.request_id if latest_run else "",
            user_id,
        ) if latest_run else []

        recent_actions = [
            f"{e.agent_name}: {e.event_type.replace('_', ' ').title()}"
            for e in recent_events[-4:]
        ]

        # Assemble "What is Happening?"
        active_stage = active_run.current_stage if active_run else "IDLE"
        if is_user_running or active_run:
            headline = f"CareerOS is currently active: {active_stage}"
            curr_state = f"Operating stage: {active_stage}"
        elif active_lifecycles:
            headline = f"Tracking {len(active_lifecycles)} active applications across hiring pipelines."
            curr_state = f"Tracking {len(active_lifecycles)} active opportunities"
        else:
            headline = "CareerOS is monitoring opportunities and awaiting next scheduled cycle."
            curr_state = "Idle & Monitoring"

        top_score = None
        top_title = None
        if latest_run and latest_run.metadata:
            top_matches = latest_run.metadata.get("top_matches", [])
            if top_matches:
                top_score = top_matches[0].get("score")
                top_title = top_matches[0].get("title")

        happening = WhatIsHappeningSection(
            headline=headline,
            active_stage=active_stage,
            is_actively_running=is_user_running or (active_run is not None),
            jobs_evaluated=latest_run.metadata.get("jobs_discovered", 0) if latest_run and latest_run.metadata else 0,
            top_match_title=top_title,
            top_match_score=top_score,
            scams_blocked=latest_run.metadata.get("scams_blocked", 0) if latest_run and latest_run.metadata else 0,
            active_applications_count=len(active_lifecycles),
            recent_agent_actions=recent_actions,
        )

        # Assemble "What Needs Me?"
        action_items: list[dict[str, Any]] = []
        for a in approvals:
            action_items.append({
                "type": "APPROVAL_REQUIRED",
                "id": str(a.id),
                "title": f"Application Approval: {a.action_type}",
                "description": f"Role requires authorization under {a.policy_gate} safety policy.",
                "target_url": "/command-center",
            })

        for u in unconfirmed[:2]:
            action_items.append({
                "type": "CONFIRM_SKILL",
                "id": u.id,
                "title": f"Confirm Experience: {u.key.replace('skill:', '').title()}",
                "description": u.content,
                "target_url": "/profile",
            })

        needs_me = WhatNeedsMeSection(
            total_actions_required=len(approvals) + len(unconfirmed[:2]),
            pending_approvals_count=len(approvals),
            unconfirmed_skills_count=len(unconfirmed),
            pending_follow_ups_count=sum(
                len([f for f in lc.follow_up_recommendations if f.status == "PENDING"])
                for lc in lifecycles
            ),
            action_items=action_items,
        )

        # Assemble "What Should I Do Next?"
        next_actions: list[NextActionItem] = []

        # Check for upcoming interview stages
        interview_lcs = [
            lc for lc in active_lifecycles
            if lc.current_status in ("ASSESSMENT", "INTERVIEW", "TECHNICAL", "HR")
        ]
        for ilc in interview_lcs:
            next_actions.append(
                NextActionItem(
                    action_type="INTERVIEW_PREP",
                    priority="HIGH",
                    title=f"Review Preparation Plan for {ilc.current_status}",
                    description=f"Tailored question prep and talking points are ready for application {ilc.application_id[:8]}.",
                    target_url=f"/applications/{ilc.application_id}",
                )
            )

        # Check for learning gaps
        learning_gaps = [m for m in memories if m.category == "LEARNING_GAP"]
        if learning_gaps:
            top_gap = learning_gaps[0]
            next_actions.append(
                NextActionItem(
                    action_type="EVIDENCE_GAP",
                    priority="MEDIUM",
                    title=f"Evidence Skill Gap: {top_gap.key.replace('learning_gap:', '').title()}",
                    description=top_gap.content,
                    target_url="/profile",
                )
            )

        # Default proactive recommendation if empty
        if not next_actions:
            next_actions.append(
                NextActionItem(
                    action_type="CONNECT",
                    priority="LOW",
                    title="Review High-Signal Networking Recommendations",
                    description="Outreach Agent identified 3 relevant connections in your target domain.",
                    target_url="/network",
                )
            )

        should_do_next = WhatShouldIDoNextSection(recommendations=next_actions)

        return OperatingStateResponse(
            user_id=u_str,
            current_operating_state=curr_state,
            what_is_happening=happening,
            what_needs_me=needs_me,
            what_should_i_do_next=should_do_next,
        )
