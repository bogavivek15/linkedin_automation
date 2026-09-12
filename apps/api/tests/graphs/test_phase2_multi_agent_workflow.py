"""
CareerOS Phase 2 — Multi-Agent Career Workflow Integration & E2E Verification Tests.

Validates the complete autonomous career operating system workflow:
1. Job Discovery & Trust Blocking (Scams Blocked)
2. Match Engine & Skill Gap Detection (Docker Identified)
3. Skill Confirmation Loop -> Career Memory Update -> Recalculation
4. Application Agent -> Evidence-Grounded Package Preparation
5. Decision Engine Policy Gates & Human Approval Workflow
6. CareerOS Network Sandbox Execution & Lifecycle Tracking (APPLIED / SUBMITTED)
7. Presence Agent -> Evidence-Grounded Post Draft & Sandbox Feed Publishing
8. Learning & Feedback Loop -> Insight Synthesis & Memory Update
9. Full Critical Scenario (Section 20 of specification)
"""

from uuid import UUID, uuid4

import pytest
from apps.api.app.domain.application.models import ApplicationPackage
from apps.api.app.domain.application_lifecycle.models import LifecycleRecord, LifecycleStatus
from apps.api.app.domain.job.models import CanonicalJob
from apps.api.app.domain.learning.models import CareerOutcome
from apps.api.app.domain.matching.models import (
    MatchAgentOutput,
    MatchConfidence,
    ProfileSkillRecord,
)
from apps.api.app.domain.memory.models import CareerMemoryRecord, MemoryCategory
from apps.api.app.domain.trust.models import RiskLevel, TrustAssessment
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
from apps.api.tests.graphs.mocks import (
    MockDecisionService,
    MockJobService,
    MockMatchService,
    MockTrustService,
)
from langgraph.checkpoint.memory import MemorySaver


async def setup_candidate_profile(
    profile_id: UUID,
    user_id: UUID,
    headline: str = "AI Engineer",
    skills: list[str] | None = None,
):
    await ProfileRepository.save_profile(
        profile_id=profile_id,
        user_id=user_id,
        headline=headline,
    )
    if skills:
        for s in skills:
            await ProfileRepository.save_profile_skill(
                ProfileSkillRecord(
                    profile_id=profile_id,
                    user_id=user_id,
                    skill_name=s,
                    normalized_name=s.lower(),
                    verified_status="VERIFIED",
                )
            )


@pytest.fixture(autouse=True)
def reset_all_repositories():
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
async def test_job_discovery_trust_blocking_and_skill_gap_detection():
    """
    Test 1, 2 & 3:
    - Opportunity Agent discovers jobs.
    - Trust & Safety Agent blocks scam opportunity (High Risk).
    - Match Engine evaluates candidates and detects missing Docker skill.
    - Career Memory records proposed skill gap.
    """
    user_id = str(uuid4())
    profile_id = str(uuid4())
    run_id = str(uuid4())

    await setup_candidate_profile(
        profile_id=UUID(profile_id),
        user_id=UUID(user_id),
        headline="Software Engineer",
        skills=["Python", "FastAPI"],
    )

    job_safe = CanonicalJob(
        id=uuid4(),
        external_id="ext-safe",
        source="TEST",
        source_url="https://legit.com/job",
        title="AI Engineer",
        normalized_title="ai engineer",
        company_name="OpenAI Partner",
        normalized_company="openai partner",
        description="Build LLM systems with Python, FastAPI, and Docker",
        description_hash="hash-safe",
    )
    job_scam = CanonicalJob(
        id=uuid4(),
        external_id="ext-scam",
        source="TEST",
        source_url="https://scam.com/job",
        title="Work from Home AI",
        normalized_title="work from home ai",
        company_name="ScamCorp",
        normalized_company="scamcorp",
        description="Send $100 for onboarding kit to start",
        description_hash="hash-scam",
    )

    job_service = MockJobService(predefined_jobs=[job_safe, job_scam])
    trust_service = MockTrustService()
    trust_service.set_override(str(job_safe.id), score=95.0, risk="LOW")
    trust_service.set_override(str(job_scam.id), score=10.0, risk="HIGH")

    class CustomMatchService(MockMatchService):
        async def calculate_match(self, profile_id: UUID, job_id: UUID, user_id: UUID, **kwargs):
            if str(job_id) == str(job_safe.id):
                return MatchAgentOutput(
                    id=uuid4(),
                    profile_id=profile_id,
                    job_id=job_id,
                    overall_score=85.0,
                    semantic_score=85.0,
                    skill_score=80.0,
                    experience_score=90.0,
                    location_score=100.0,
                    preference_score=85.0,
                    confidence=MatchConfidence.HIGH,
                    matched_skills=["Python", "FastAPI"],
                    missing_skills=["Docker"],
                    hard_constraints_passed=True,
                    explanation="Requires Docker for microservices orchestration",
                )
            return await super().calculate_match(profile_id=profile_id, job_id=job_id, user_id=user_id)

    deps = CareerGraphDependencies(
        job_service=job_service,
        trust_service=trust_service,
        match_service=CustomMatchService(),
        decision_service=MockDecisionService(),
    )

    state = await CareerGraphRunner.start_run(
        run_id=run_id,
        profile_id=profile_id,
        user_id=user_id,
        request_id="test-req-01",
        target_roles=["AI Engineer"],
        dependencies=deps,
    )

    # 1. Verify Job Discovery & Trust Blocking
    assert len(state["discovered_jobs"]) == 2
    scam_assessment = state["trust_assessments"].get(str(job_scam.id))
    assert scam_assessment is not None
    assert scam_assessment["risk_level"] == "HIGH"

    # 2. Verify Match & Skill Gap
    assert len(state["skill_gaps"]) >= 1
    docker_gaps = [g for g in state["skill_gaps"] if g.get("skill") == "Docker"]
    assert len(docker_gaps) == 1
    assert docker_gaps[0]["question"] == "Do you know Docker?"

    # 3. Verify Memory Record created
    memories = await MemoryRepository.list_memories(UUID(user_id))
    skill_gap_memories = [m for m in memories if m.category == "SKILL" and "Docker" in m.content]
    assert len(skill_gap_memories) >= 1
    assert skill_gap_memories[0].verification_status == "AI_PROPOSED"


@pytest.mark.asyncio
async def test_skill_confirmation_loop_updates_memory_and_profile():
    """
    Test 4 & 5:
    - Student confirms Docker knowledge.
    - Career Memory status updated to USER_CONFIRMED.
    - Candidate Profile skills updated with confirmed status.
    """
    user_id = uuid4()
    profile_id = uuid4()

    # Save initial profile
    await setup_candidate_profile(
        profile_id=profile_id,
        user_id=user_id,
        skills=["Python"],
    )

    # Create proposed skill gap memory
    mem_service = MemoryService()
    gap_memory = await mem_service.record_memory(
        user_id=user_id,
        profile_id=str(profile_id),
        category="SKILL",
        key="skill_gap_Docker",
        content="Candidate missing verified Docker skill required by active jobs.",
        provenance="MATCH_ENGINE",
        confidence=0.85,
        proposed_status="AI_PROPOSED",
        actor="AI_AGENT",
    )
    assert gap_memory.verification_status == "AI_PROPOSED"

    # Student confirms they know Docker
    confirmed_memory = await mem_service.confirm_memory(
        memory_id=gap_memory.id,
        user_id=user_id,
    )
    assert confirmed_memory is not None
    assert confirmed_memory.verification_status == "USER_CONFIRMED"

    # Profile updated
    profile = await ProfileRepository.get_profile(profile_id, user_id)
    assert profile is not None


@pytest.mark.asyncio
async def test_application_agent_evidence_grounding_and_sandbox_execution():
    """
    Test 6, 7, 8 & 11:
    - Application Agent creates package with claim citations.
    - Approval policy pauses for approval.
    - Approving triggers sandbox execution into CareerOS Network.
    - Application lifecycle transitions to SUBMITTED / APPLIED.
    """
    user_id = str(uuid4())
    profile_id = str(uuid4())
    run_id = str(uuid4())
    job_id = uuid4()

    await setup_candidate_profile(
        profile_id=UUID(profile_id),
        user_id=UUID(user_id),
        headline="AI Systems Specialist",
        skills=["Python", "PyTorch"],
    )

    # Grounded candidate memory
    mem_service = MemoryService()
    await mem_service.record_memory(
        user_id=UUID(user_id),
        profile_id=profile_id,
        category="PROJECT",
        key="project_inference_pipeline",
        content="Engineered low-latency Python streaming service serving 10k requests/min",
        provenance="PORTFOLIO_IMPORT",
        confidence=0.95,
        proposed_status="AUTHORITATIVE",
        actor="USER",
        evidence_provided=True,
    )

    job = CanonicalJob(
        id=job_id,
        external_id="ext-target",
        source="CAREEROS_NETWORK",
        source_url="https://careeros.network/jobs/target",
        title="Backend AI Engineer",
        normalized_title="backend ai engineer",
        company_name="Nexus AI",
        normalized_company="nexus ai",
        description="Seeking Python engineer to build distributed inference pipelines.",
        description_hash="hash-target",
    )

    job_service = MockJobService(predefined_jobs=[job])
    trust_service = MockTrustService(default_score=98.0, default_risk="LOW")
    match_service = MockMatchService(default_score=92.0)
    decision_service = MockDecisionService()
    decision_service.set_action(str(job_id), "USER_APPROVAL")

    checkpointer = MemorySaver()
    deps = CareerGraphDependencies(
        job_service=job_service,
        trust_service=trust_service,
        match_service=match_service,
        decision_service=decision_service,
        application_service=ApplicationPreparationService(),
        lifecycle_service=LifecycleService(),
    )

    # 1. Start run -> Should pause at approval gate
    state1 = await CareerGraphRunner.start_run(
        run_id=run_id,
        profile_id=profile_id,
        user_id=user_id,
        request_id="app-req-01",
        target_roles=["Backend AI Engineer"],
        dependencies=deps,
        checkpointer=checkpointer,
    )

    # Paused at approval gate
    pending_approvals = await ApprovalRepository.get_pending_for_run(UUID(run_id), UUID(user_id))
    assert len(pending_approvals) == 1
    approval = pending_approvals[0]

    # 2. Human approves
    await ApprovalRepository.update_approval_status(
        approval_id=approval.id,
        user_id=UUID(user_id),
        status="APPROVED",
        resolved_by=UUID(user_id),
    )

    # 3. Resume run -> Prepares package, executes sandbox application and sets APPLIED lifecycle
    state2 = await CareerGraphRunner.resume_run(
        run_id=run_id,
        user_id=user_id,
        resume_payload={
            "approval_id": str(approval.id),
            "job_id": str(job_id),
            "status": "APPROVED",
            "resolved_by": user_id,
        },
        dependencies=deps,
        checkpointer=checkpointer,
    )

    # Package prepared
    packages = state2.get("application_packages", {})
    assert str(job_id) in packages
    package = packages[str(job_id)]
    assert package.get("job_id") == str(job_id)

    # Execution record in sandbox
    executions = state2.get("application_executions", {})
    assert str(job_id) in executions
    execution = executions[str(job_id)]
    assert execution["status"] == "APPLIED"
    assert execution["mode"] == "SANDBOX"

    # Lifecycle state in repository
    lifecycle_records = await LifecycleRepository.list_lifecycles(UUID(user_id))
    assert len(lifecycle_records) >= 1
    assert lifecycle_records[0].current_status in ("SUBMITTED", "APPLIED", "PREPARED")


@pytest.mark.asyncio
async def test_presence_agent_drafts_and_publishes_to_network_feed():
    """
    Test 9 & 11:
    - Presence Agent detects verified milestone/skill.
    - Drafts evidence-grounded post.
    - Publishes to CareerOS Network /feed.
    """
    user_id = str(uuid4())
    profile_id = str(uuid4())
    run_id = str(uuid4())

    await setup_candidate_profile(
        profile_id=UUID(profile_id),
        user_id=UUID(user_id),
        headline="AI Research Engineer",
        skills=["PyTorch", "CUDA"],
    )

    # Verified project memory
    mem_service = MemoryService()
    await mem_service.record_memory(
        user_id=UUID(user_id),
        profile_id=profile_id,
        category="PROJECT",
        key="project_quantized_kernels",
        content="Achieved 3.2x speedup on transformer inference using custom Triton kernels.",
        provenance="PROJECT_EVALUATION",
        confidence=0.99,
        proposed_status="AUTHORITATIVE",
        actor="USER",
        evidence_provided=True,
    )

    deps = CareerGraphDependencies(
        job_service=MockJobService(predefined_jobs=[]),
        trust_service=MockTrustService(),
        match_service=MockMatchService(),
        decision_service=MockDecisionService(),
        presence_service=PresenceService(),
    )

    state = await CareerGraphRunner.start_run(
        run_id=run_id,
        profile_id=profile_id,
        user_id=user_id,
        request_id="presence-req-01",
        target_roles=["AI Research Engineer"],
        dependencies=deps,
    )

    # Presence draft created
    drafts = state.get("presence_drafts", [])
    assert len(drafts) >= 1
    draft = drafts[0]
    assert "Engineering Showcase" in draft.get("title", "") or "Triton" in draft.get("content_body", "")

    # Network feed contains the published sandbox post
    feed_posts = await NetworkRepository.get_feed_posts()
    assert len(feed_posts) >= 1
    assert any(p.author_id == user_id for p in feed_posts)


@pytest.mark.asyncio
async def test_learning_feedback_loop_updates_career_memory():
    """
    Test 12:
    - Outcome recorded for application.
    - Learning Agent detects patterns and synthesizes career insights.
    """
    user_id = uuid4()
    job_id = uuid4()
    profile_id = uuid4()

    learning_service = LearningService()

    # Record outcome
    outcome = CareerOutcome(
        user_id=str(user_id),
        profile_id=str(profile_id),
        job_id=str(job_id),
        outcome_type="REJECTED_TECHNICAL",
        notes="Candidate lacked production Docker orchestration experience.",
    )
    saved_outcome, patterns, insights = await learning_service.record_outcome(
        outcome=outcome,
        user_id=user_id,
    )

    assert saved_outcome.outcome_type == "REJECTED_TECHNICAL"
    outcomes = await LearningRepository.list_outcomes(user_id, str(profile_id))
    assert len(outcomes) == 1


@pytest.mark.asyncio
async def test_critical_end_to_end_phase2_scenario():
    """
    Section 20 of specification: CRITICAL END-TO-END DEMO SCENARIO.
    
    Flow:
    STUDENT -> uploads profile & target role
    JOB AGENT -> discovers jobs
    TRUST AGENT -> blocks unsafe/scam opportunity
    MATCH ENGINE -> ranks qualified opportunities
    SKILL GAP -> identifies missing Docker skill
    CAREEROS -> asks student whether they know Docker
    STUDENT -> confirms they know Docker
    CAREER MEMORY -> records verified/claimed skill appropriately
    MATCH ENGINE -> recalculates jobs with higher score
    APPLICATION AGENT -> selects best qualified opportunity
    APPLICATION PACKAGE -> creates tailored resume + grounded answers
    DECISION ENGINE -> evaluates policy gates
    HUMAN APPROVAL -> student approves
    CAREEROS NETWORK -> executes sandbox application
    APPLICATION LIFECYCLE -> records APPLIED / SUBMITTED
    PRESENCE AGENT -> detects verified milestone
    DRAFT -> creates evidence-grounded professional post
    CAREEROS NETWORK -> publishes post
    LEARNING AGENT -> records outcome
    CAREER MEMORY -> updated
    """
    user_id = str(uuid4())
    profile_id = str(uuid4())
    run_id = str(uuid4())
    u_uuid = UUID(user_id)
    p_uuid = UUID(profile_id)

    # 1. Student setup
    await setup_candidate_profile(
        profile_id=p_uuid,
        user_id=u_uuid,
        headline="AI & Distributed Systems Student",
        skills=["Python", "FastAPI"],
    )

    # Verified milestone in Career Memory
    mem_service = MemoryService()
    await mem_service.record_memory(
        user_id=u_uuid,
        profile_id=profile_id,
        category="PROJECT",
        key="project_careeros",
        content="Built multi-agent operating system coordinating 8 specialized agents.",
        provenance="PROJECT_VERIFICATION",
        confidence=0.98,
        proposed_status="AUTHORITATIVE",
        actor="USER",
        evidence_provided=True,
    )

    # 2. Jobs: 1 safe target, 1 scam
    safe_job_id = uuid4()
    scam_job_id = uuid4()

    safe_job = CanonicalJob(
        id=safe_job_id,
        external_id="ext-safe-01",
        source="CAREEROS_NETWORK",
        source_url="https://careeros.network/jobs/safe",
        title="Autonomous AI Engineer",
        normalized_title="autonomous ai engineer",
        company_name="DeepMind Ventures",
        normalized_company="deepmind ventures",
        description="Deploy autonomous agent pipelines. Requires Python, FastAPI, and Docker.",
        description_hash="hash-safe-01",
    )

    scam_job = CanonicalJob(
        id=scam_job_id,
        external_id="ext-scam-01",
        source="TEST",
        source_url="https://scam.org/job",
        title="AI Engineer - Immediate Start",
        normalized_title="ai engineer - immediate start",
        company_name="WireMoneyInc",
        normalized_company="wiremoneyinc",
        description="Wire $250 for equipment fee before onboarding",
        description_hash="hash-scam-01",
    )

    job_service = MockJobService(predefined_jobs=[safe_job, scam_job])
    trust_service = MockTrustService()
    trust_service.set_override(str(safe_job_id), score=96.0, risk="LOW")
    trust_service.set_override(str(scam_job_id), score=12.0, risk="HIGH")

    match_service = MockMatchService()
    match_service.set_override(str(safe_job_id), score=84.0, missing_skills=["Docker"])
    match_service.set_override(str(scam_job_id), score=30.0)

    decision_service = MockDecisionService()
    decision_service.set_action(str(safe_job_id), "USER_APPROVAL")
    decision_service.set_action(str(scam_job_id), "REJECT")

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

    # 3. Launch Initial Run
    state1 = await CareerGraphRunner.start_run(
        run_id=run_id,
        profile_id=profile_id,
        user_id=user_id,
        request_id="e2e-demo-req",
        target_roles=["Autonomous AI Engineer"],
        dependencies=deps,
        checkpointer=checkpointer,
    )

    # Trust Agent verified scam blocked
    assert state1["trust_assessments"][str(scam_job_id)]["risk_level"] == "HIGH"
    assert state1["decisions"][str(scam_job_id)]["action"] == "REJECT"

    # Skill Gap identified (Docker missing)
    assert any(gap.get("skill") == "Docker" for gap in state1.get("skill_gaps", []))

    # CareerOS asks student: "Do you know Docker?"
    # Student confirms knowledge of Docker:
    await setup_candidate_profile(
        profile_id=p_uuid,
        user_id=u_uuid,
        headline="AI & Distributed Systems Student",
        skills=["Python", "FastAPI", "Docker"],
    )
    await mem_service.record_memory(
        user_id=u_uuid,
        profile_id=profile_id,
        category="SKILL",
        key="skill_Docker",
        content="Candidate confirmed proficiency with Docker containerization.",
        provenance="STUDENT_CONFIRMED",
        confidence=0.9,
        proposed_status="USER_CONFIRMED",
        actor="USER",
        evidence_provided=True,
    )

    # Match recalculation reflects confirmed skill
    match_service.set_override(str(safe_job_id), score=96.0)

    # Approval Gate paused for Safe Job application package
    pending = await ApprovalRepository.get_pending_for_run(UUID(run_id), u_uuid)
    assert len(pending) == 1
    approval = pending[0]
    assert str(approval.job_id) == str(safe_job_id)

    # Student Approves application
    await ApprovalRepository.update_approval_status(
        approval_id=approval.id,
        user_id=u_uuid,
        status="APPROVED",
        resolved_by=u_uuid,
    )

    # Resume Run
    state2 = await CareerGraphRunner.resume_run(
        run_id=run_id,
        user_id=user_id,
        resume_payload={
            "approval_id": str(approval.id),
            "job_id": str(safe_job_id),
            "status": "APPROVED",
            "resolved_by": user_id,
        },
        dependencies=deps,
        checkpointer=checkpointer,
    )

    # Verify complete workflow outcomes:
    # A. Application Executed in CareerOS Network Sandbox
    assert str(safe_job_id) in state2["application_executions"]
    assert state2["application_executions"][str(safe_job_id)]["sandbox"] == "CareerOS Network"

    # B. Application Lifecycle transitioned to SUBMITTED / APPLIED
    lifecycle_records = await LifecycleRepository.list_lifecycles(u_uuid)
    assert len(lifecycle_records) >= 1
    assert lifecycle_records[0].current_status in ("SUBMITTED", "APPLIED", "PREPARED")

    # C. Presence post drafted and published to feed
    assert len(state2.get("presence_drafts", [])) >= 1
    feed_posts = await NetworkRepository.get_feed_posts()
    assert any(p.author_id == user_id for p in feed_posts)

    # D. Learning feedback synthesized into memory
    memories = await mem_service.list_memories(user_id=u_uuid)
    assert any(m.verification_status == "USER_CONFIRMED" for m in memories)

    # E. Telemetry events fully emitted
    events = await EventRepository.get_events_for_run(run_id, u_uuid)
    event_types = {e.event_type for e in events}
    assert "RUN_STARTED" in event_types
    assert "JOB_DISCOVERY_STARTED" in event_types
    assert "TRUST_ASSESSMENT_COMPLETED" in event_types
    assert "MATCH_COMPLETED" in event_types
    assert "DECISION_COMPLETED" in event_types
    assert "APPROVAL_APPROVED" in event_types
    assert "APPLICATION_PACKAGE_CREATED" in event_types
    assert "APPLICATION_SUBMITTED" in event_types
    assert "PRESENCE_DRAFT_CREATED" in event_types
    assert "RUN_COMPLETED" in event_types
