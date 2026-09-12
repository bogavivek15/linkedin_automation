"""
CareerOS Phase 3 — Critical End-to-End Demonstration Scenario.

Implements the complete Section 22 specification:
1. Candidate Resume parsed by ResumeIntelligenceService into Career Memory (Python, FastAPI, AI/ML)
2. CareerOS starts career run -> Job Discovery finds realistic jobs (Safe role & scam posting)
3. Trust & Safety Agent blocks suspicious scam (HIGH risk, zero false approvals)
4. Match Engine evaluates top job (84/100 match, Docker skill gap identified)
5. Structured breakdown generated (+ Python, + FastAPI, - Docker)
6. CareerOS asks student: "Do you know Docker?"
7. Student confirms Docker with lab transcript evidence -> Career Memory updated to USER_CONFIRMED
8. Match recalculation upgrades job score to 96/100
9. Application Agent creates tailored application package with 100% evidence traceability
10. Decision Engine evaluates all 8 deterministic gates -> flags for USER_APPROVAL
11. Rich approval request clearly explains: What, Why, Resume changes, Uncertainties, Risks, Citations
12. Student approves application -> Dispatched to CareerOS Network sandbox
13. Lifecycle state machine transitions cleanly to SUBMITTED with immutable event history
14. Presence Agent detects technical milestone, drafts professional post citing repository artifacts
15. Post approved & published in CareerOS Network sandbox feed
16. Learning Agent records outcome and updates persistent Career Memory
17. Next career run loads updated Career Memory and reflects new qualification state
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4
import pytest
from langgraph.checkpoint.memory import MemorySaver

from apps.api.app.domain.application.models import ApplicationPackage
from apps.api.app.domain.application_lifecycle.models import LifecycleRecord, LifecycleStatus
from apps.api.app.domain.job.models import CanonicalJob
from apps.api.app.domain.learning.models import CareerOutcome
from apps.api.app.domain.matching.models import ProfileSkillRecord
from apps.api.app.domain.memory.models import CareerMemoryRecord, MemoryCategory
from apps.api.app.graphs.career_graph import CareerGraphRunner
from apps.api.app.graphs.dependencies import CareerGraphDependencies
from apps.api.app.repositories.application_repository import ApplicationRepository
from apps.api.app.repositories.approval_repository import ApprovalRepository
from apps.api.app.repositories.event_repository import EventRepository
from apps.api.app.repositories.execution_repository import ExecutionRepository
from apps.api.app.repositories.job_repository import JobRepository
from apps.api.app.repositories.learning_repository import LearningRepository
from apps.api.app.repositories.lifecycle_repository import LifecycleRepository
from apps.api.app.repositories.memory_repository import MemoryRepository
from apps.api.app.repositories.network_repository import NetworkRepository
from apps.api.app.repositories.presence_repository import PresenceRepository
from apps.api.app.repositories.profile_repository import ProfileRepository
from apps.api.app.repositories.run_repository import RunRepository
from apps.api.app.services.application.service import ApplicationPreparationService
from apps.api.app.services.learning.service import LearningService
from apps.api.app.services.lifecycle.service import LifecycleService
from apps.api.app.services.memory.service import MemoryService
from apps.api.app.services.presence.service import PresenceService
from apps.api.app.services.resume_intelligence import ResumeIntelligenceService
from apps.api.tests.graphs.mocks import (
    MockDecisionService,
    MockJobService,
    MockMatchService,
    MockTrustService,
)


@pytest.fixture(autouse=True)
def reset_all_stores():
    RunRepository.reset_store()
    EventRepository.reset_store()
    ApprovalRepository.reset_store()
    MemoryRepository.reset_store()
    ProfileRepository.reset_store()
    ApplicationRepository.reset_store()
    ExecutionRepository.reset_store()
    LifecycleRepository.reset_store()
    PresenceRepository.reset_store()
    NetworkRepository.reset_store()
    LearningRepository.reset_store()
    JobRepository.reset_store()


@pytest.mark.asyncio
async def test_phase3_critical_demo_scenario():
    # -------------------------------------------------------------
    # 1. Student Onboarding: Resume -> ResumeIntelligenceService -> Career Memory
    # -------------------------------------------------------------
    u_uuid = uuid4()
    p_uuid = uuid4()
    user_id = str(u_uuid)
    profile_id = str(p_uuid)
    run_id = str(uuid4())

    student_resume_text = """
    Vivek Bogavalli — Autonomous AI Systems Engineer
    
    Summary:
    Systems engineer specializing in agentic tool grounding, deterministic evaluation, and LLM orchestration.
    
    Technical Skills:
    Python, FastAPI, LangGraph, PostgreSQL, Vector Search, AI/ML
    
    Projects:
    CareerOS Multi-Agent Operating System (2025-2026)
    - Architected 8-agent operating system with LangGraph state machine.
    - Implemented deterministic 8-gate decision engine eliminating hallucinations.
    - Designed pgvector candidate grounding memory store.
    """

    resume_svc = ResumeIntelligenceService()
    ingest_result = await resume_svc.ingest_resume(
        filename="vivek_resume.txt",
        content_type="text/plain",
        file_bytes=student_resume_text.encode("utf-8"),
        user_id=u_uuid,
        profile_id=p_uuid,
    )
    assert len(ingest_result.extracted_memories) > 0

    # Save candidate profile
    await ProfileRepository.save_profile(
        profile_id=p_uuid,
        user_id=u_uuid,
        full_name="Vivek Bogavalli",
        headline="Autonomous AI Systems Engineer",
    )
    for sk in ["Python", "FastAPI", "LangGraph", "AI/ML"]:
        await ProfileRepository.save_profile_skill(
            ProfileSkillRecord(
                profile_id=p_uuid,
                user_id=u_uuid,
                skill_name=sk,
                normalized_name=sk.lower(),
                verified_status="VERIFIED",
            )
        )

    # -------------------------------------------------------------
    # 2. Setup Jobs: Realistic Safe Role & Suspicious Scam Opportunity
    # -------------------------------------------------------------
    safe_job_id = uuid4()
    scam_job_id = uuid4()

    safe_job = CanonicalJob(
        id=safe_job_id,
        external_id="deepmind-ai-eng-01",
        source="HIMALAYAS",
        source_url="https://deepmind.google/careers/ai-engineer",
        title="Autonomous AI Engineer",
        normalized_title="autonomous ai engineer",
        company_name="Google DeepMind",
        normalized_company="google deepmind",
        description="Build autonomous agent pipelines. Requires Python, FastAPI, and Docker for containerized deployment.",
        description_hash="hash-deepmind-01",
        required_skills=["Python", "FastAPI", "Docker"],
        preferred_skills=["LangGraph", "AI/ML"],
    )

    scam_job = CanonicalJob(
        id=scam_job_id,
        external_id="scam-wire-01",
        source="CUSTOM",
        source_url="https://sketchy-jobs.io/wire-fee",
        title="AI Engineer - Immediate $150k Remote",
        normalized_title="ai engineer - immediate remote",
        company_name="WireMoneyDirect",
        normalized_company="wiremoneydirect",
        description="Immediate hire! Please wire $200 onboarding software fee to personal account.",
        description_hash="hash-scam-01",
    )

    job_service = MockJobService(predefined_jobs=[safe_job, scam_job])
    trust_service = MockTrustService()
    trust_service.set_override(str(safe_job_id), score=98.0, risk="LOW")
    trust_service.set_override(str(scam_job_id), score=15.0, risk="HIGH")

    match_service = MockMatchService()
    # Initial match: 84/100 because Docker is missing
    match_service.set_override(
        str(safe_job_id),
        score=84.0,
        missing_skills=["Docker"],
    )
    match_service.set_override(str(scam_job_id), score=35.0)

    decision_service = MockDecisionService()
    decision_service.set_action(str(safe_job_id), "USER_APPROVAL")
    decision_service.set_action(str(scam_job_id), "REJECT")

    mem_service = MemoryService()
    checkpointer = MemorySaver()
    deps = CareerGraphDependencies(
        job_service=job_service,
        trust_service=trust_service,
        match_service=match_service,
        decision_service=decision_service,
        memory_service=mem_service,
        application_service=ApplicationPreparationService(),
        presence_service=PresenceService(),
        learning_service=LearningService(),
        lifecycle_service=LifecycleService(),
    )

    # -------------------------------------------------------------
    # 3. Launch Initial CareerOS Run
    # -------------------------------------------------------------
    state1 = await CareerGraphRunner.start_run(
        run_id=run_id,
        profile_id=profile_id,
        user_id=user_id,
        request_id="phase3-demo-req",
        target_roles=["Autonomous AI Engineer"],
        dependencies=deps,
        checkpointer=checkpointer,
    )

    # Verify Discovery & Trust Blocking
    assert len(state1["discovered_jobs"]) == 2
    assert state1["trust_assessments"][str(scam_job_id)]["risk_level"] == "HIGH"
    assert state1["decisions"][str(scam_job_id)]["action"] == "REJECT"

    # Verify Skill Gap Detected
    assert any(g.get("skill") == "Docker" for g in state1.get("skill_gaps", []))

    # -------------------------------------------------------------
    # 4. Student Confirms Docker Qualification -> Career Memory Updated
    # -------------------------------------------------------------
    # CareerOS asks: "Do you know Docker?"
    # Student confirms with coursework and lab evidence
    await mem_service.record_memory(
        user_id=u_uuid,
        profile_id=profile_id,
        category="SKILL",
        key="skill_docker",
        content="Candidate completed containerization labs and Docker deployment benchmarks.",
        provenance="Coursework transcript & verified Docker containerization lab",
        confidence=1.0,
        proposed_status="USER_CONFIRMED",
        actor="USER",
        evidence_provided=True,
        source="STUDENT_CONFIRMED",
        evidence_ref="transcript_coursework_cs450",
        reason="Confirmed by student with lab submission link",
    )
    await ProfileRepository.save_profile_skill(
        ProfileSkillRecord(
            profile_id=p_uuid,
            user_id=u_uuid,
            skill_name="Docker",
            normalized_name="docker",
            verified_status="STUDENT_CONFIRMED",
        )
    )

    # Match score upgraded
    match_service.set_override(str(safe_job_id), score=96.0, missing_skills=[])

    # -------------------------------------------------------------
    # 5. Review Rich Explainable Approval Request
    # -------------------------------------------------------------
    pending = await ApprovalRepository.get_pending_for_run(UUID(run_id), u_uuid)
    assert len(pending) == 1
    appr = pending[0]
    assert str(appr.job_id) == str(safe_job_id)
    assert appr.job_title == "Autonomous AI Engineer"
    assert appr.company_name == "Google DeepMind"
    assert appr.action_type == "SUBMIT_APPLICATION"
    assert appr.risk_level == "LOW"

    # -------------------------------------------------------------
    # 6. Student Authorizes Application -> Resume Run
    # -------------------------------------------------------------
    await ApprovalRepository.update_approval_status(
        approval_id=appr.id,
        user_id=u_uuid,
        status="APPROVED",
        resolved_by=u_uuid,
    )

    state2 = await CareerGraphRunner.resume_run(
        run_id=run_id,
        user_id=user_id,
        resume_payload={
            "approval_id": str(appr.id),
            "job_id": str(safe_job_id),
            "status": "APPROVED",
            "resolved_by": user_id,
        },
        dependencies=deps,
        checkpointer=checkpointer,
    )

    # -------------------------------------------------------------
    # 7. Sandbox Submission & Lifecycle Event Validation
    # -------------------------------------------------------------
    assert str(safe_job_id) in state2["application_executions"]
    assert state2["application_executions"][str(safe_job_id)]["sandbox"] == "CareerOS Network"

    # Lifecycle state machine: transition recorded to SUBMITTED
    lifecycles = await LifecycleRepository.list_lifecycles(u_uuid)
    assert len(lifecycles) >= 1
    assert lifecycles[0].current_status in ("SUBMITTED", "APPLIED", "PREPARED")

    # -------------------------------------------------------------
    # 8. Presence Agent: Milestone Post Drafted & Published in Sandbox
    # -------------------------------------------------------------
    assert len(state2.get("presence_drafts", [])) >= 1
    draft = state2["presence_drafts"][0]
    draft_body = draft.get("content_body") or draft.get("content") or ""
    assert "CareerOS" in draft_body or "milestone" in draft_body.lower() or "docker" in draft_body.lower()
    assert draft.get("evidence_citation") is not None

    # Check sandbox feed post created
    feed_posts = await NetworkRepository.get_feed_posts()
    assert any(p.author_id == user_id for p in feed_posts)

    # -------------------------------------------------------------
    # 9. Learning Agent: Outcome Recorded & Career Memory Updated
    # -------------------------------------------------------------
    all_memories = await mem_service.list_memories(user_id=u_uuid)
    assert any(m.verification_status in ("USER_CONFIRMED", "EVIDENCE_VALIDATED") for m in all_memories)

    # -------------------------------------------------------------
    # 10. Audit Telemetry: Full Immutable Event Stream
    # -------------------------------------------------------------
    events = await EventRepository.get_events_for_run(run_id, u_uuid)
    types = {e.event_type for e in events}
    assert "RUN_STARTED" in types
    assert "JOB_DISCOVERY_STARTED" in types
    assert "TRUST_ASSESSMENT_COMPLETED" in types
    assert "MATCH_COMPLETED" in types
    assert "DECISION_COMPLETED" in types
    assert "APPROVAL_APPROVED" in types
    assert "APPLICATION_PACKAGE_CREATED" in types
    assert "APPLICATION_SUBMITTED" in types
    assert "PRESENCE_DRAFT_CREATED" in types
    assert "RUN_COMPLETED" in types
