"""
CareerOS Phase 22 — End-to-End System Smoke Test.

Validates the full unified CareerOS autonomous career operating system loop:
DISCOVER
   ↓
VERIFY
   ↓
MATCH
   ↓
DECIDE
   ↓
PREPARE
   ↓
APPROVE
   ↓
EXECUTE / HANDOFF
   ↓
TRACK
   ↓
LEARN
   ↓
BUILD PRESENCE
   ↓
IMPROVE
"""

from uuid import uuid4

import pytest
from apps.api.app.domain.application.models import ApplicationPackage
from apps.api.app.domain.decision.models import CandidateAutomationPolicy
from apps.api.app.domain.decision.policy import DecisionPolicyEngine
from apps.api.app.domain.execution.context import ExecutionContext
from apps.api.app.domain.execution.policy import ExecutionPolicy
from apps.api.app.domain.learning.insights import CareerInsightGenerator
from apps.api.app.domain.learning.models import CareerOutcome
from apps.api.app.domain.learning.patterns import OutcomePatternDetector
from apps.api.app.domain.matching.models import CandidateSkill, MatchAgentOutput, SkillProvenance
from apps.api.app.domain.matching.skill_matcher import match_skills
from apps.api.app.domain.presence.policy import PresencePolicy
from apps.api.app.domain.trust.models import (
    ConfidenceLevel,
    RiskLevel,
    TrustAssessment,
)
from apps.api.app.main import app
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_full_careeros_e2e_pipeline_smoke():
    """
    Executes the comprehensive CareerOS loop from profile claims to controlled handoff,
    lifecycle progression, learning feedback, and presence generation.
    """
    user_id = str(uuid4())
    profile_id = str(uuid4())
    job_uuid = uuid4()
    job_id = str(job_uuid)

    # 1. PROFILE & VERIFIED CLAIMS
    verified_skills = [
        CandidateSkill(
            name="Python",
            normalized_name="python",
            provenance=SkillProvenance.VERIFIED,
            years_experience=2.0,
        ),
        CandidateSkill(
            name="FastAPI",
            normalized_name="fastapi",
            provenance=SkillProvenance.VERIFIED,
            years_experience=1.5,
        ),
        CandidateSkill(
            name="PostgreSQL",
            normalized_name="postgresql",
            provenance=SkillProvenance.VERIFIED,
            years_experience=2.0,
        ),
        CandidateSkill(
            name="Distributed Systems",
            normalized_name="distributed systems",
            provenance=SkillProvenance.VERIFIED,
            years_experience=1.0,
        ),
    ]

    # 2. DISCOVER & NORMALIZE JOB
    job_skills = ["Python", "FastAPI", "PostgreSQL", "Distributed Systems"]

    # 3. VERIFY TRUST (Safe employer Stripe vs Scam)
    trust_assessment = TrustAssessment(
        job_id=job_uuid,
        trust_score=94.0,
        risk_score=6.0,
        risk_level=RiskLevel.LOW,
        confidence=ConfidenceLevel.HIGH,
        positive_signals=["Verified stripe.com domain"],
        explanation="Verified legitimate enterprise employer",
    )
    assert trust_assessment.risk_level == RiskLevel.LOW

    # 4. SKILL & PROFILE MATCHING
    match_result = match_skills(job_skills, [], verified_skills)
    assert len(match_result.missing) == 0
    assert match_result.score >= 0.9

    match_output = MatchAgentOutput(
        profile_id=profile_id,
        job_id=job_id,
        semantic_score=94.0,
        skill_score=95.0,
        experience_score=88.0,
        location_score=100.0,
        preference_score=90.0,
        overall_score=92.4,
        recommended_resume_id="res-v3",
    )

    # 5. DETERMINISTIC DECISION ENGINE
    decision_engine = DecisionPolicyEngine()
    policy = CandidateAutomationPolicy(min_match_score=70.0, min_trust_score=70.0)
    decision = decision_engine.evaluate(match=match_output, trust=trust_assessment, policy=policy)
    assert decision.action in ("AUTO_APPLY", "USER_APPROVAL")
    assert decision.overall_score >= 90.0

    # 6. APPLICATION PREPARATION & APPROVAL
    pkg = ApplicationPackage(
        profile_id=profile_id,
        job_id=job_id,
        decision_id=str(decision.id),
        validation_status="APPROVED",
        cover_letter="I engineered a Raft key-value cache handling 45k req/sec.",
    )

    # 7. SAFETY & EXECUTION GATES
    exec_ctx = ExecutionContext(
        user_id=user_id,
        profile_id=profile_id,
        package=pkg,
        decision={"action": decision.action},
        requested_mode="USER_HANDOFF",
    )
    gate_eval = ExecutionPolicy.evaluate(exec_ctx)
    assert gate_eval.all_passed is True
    assert len(gate_eval.blocking_reasons) == 0

    # 8. CLOSED-LOOP LEARNING: OUTCOME -> PATTERN -> INSIGHT
    outcomes = [
        CareerOutcome(
            user_id=user_id,
            profile_id=profile_id,
            application_id=str(uuid4()),
            job_id=job_id,
            outcome_type="INTERVIEW_SCHEDULED",
            resume_version="res-v3",
            match_score=92.4,
            trust_score=94.0,
            response_time_days=1.5,
            notes="Technical screen invitation",
        ),
        CareerOutcome(
            user_id=user_id,
            profile_id=profile_id,
            application_id=str(uuid4()),
            job_id=str(uuid4()),
            outcome_type="SCREENING_PASSED",
            resume_version="res-v3",
            match_score=88.0,
            trust_score=90.0,
            response_time_days=2.0,
        ),
        CareerOutcome(
            user_id=user_id,
            profile_id=profile_id,
            application_id=str(uuid4()),
            job_id=str(uuid4()),
            outcome_type="OFFER",
            resume_version="res-v3",
            match_score=95.0,
            trust_score=96.0,
            response_time_days=3.0,
        ),
    ]
    patterns = OutcomePatternDetector.detect_patterns(
        user_id=user_id,
        profile_id=profile_id,
        outcomes=outcomes,
    )
    insights = CareerInsightGenerator.generate_insights(
        user_id=user_id,
        profile_id=profile_id,
        patterns=patterns,
    )
    assert len(insights) >= 1
    assert any("Conversion" in ins.title or "Match" in ins.title or len(ins.description) > 0 for ins in insights)

    # 9. PROFESSIONAL PRESENCE GROUNDING VALIDATION
    PresencePolicy.validate_content_grounding(
        title="Distributed Systems with Raft and FastAPI",
        content_body="Engineered a high-throughput distributed key-value cache handling 45,000 requests per second with Raft consensus.",
        evidence_ids=["mem-proj-01"],
    )

    # 10. API INTEGRATION HEALTH SMOKE
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200

        demo_resp = await client.get("/api/v1/demo/scenario")
        assert demo_resp.status_code == 200
        assert demo_resp.json()["scenario_name"] == "CareerOS Hackathon End-to-End Demo"
