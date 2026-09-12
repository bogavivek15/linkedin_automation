"""
CareerOS Phase 9.x — Graph Node Unit Tests.
"""

from uuid import uuid4

import pytest
from apps.api.app.domain.job.models import CanonicalJob
from apps.api.app.graphs.dependencies import CareerGraphDependencies
from apps.api.app.graphs.nodes.decision import evaluate_decisions_node
from apps.api.app.graphs.nodes.discover import discover_jobs_node
from apps.api.app.graphs.nodes.finalize import finalize_node
from apps.api.app.graphs.nodes.match import calculate_matches_node
from apps.api.app.graphs.nodes.trust import assess_trust_node
from apps.api.app.repositories.approval_repository import ApprovalRepository
from apps.api.app.repositories.event_repository import EventRepository
from apps.api.app.repositories.run_repository import RunRepository
from apps.api.tests.graphs.mocks import (
    MockDecisionService,
    MockJobService,
    MockMatchService,
    MockTrustService,
)


@pytest.fixture(autouse=True)
def reset_stores():
    RunRepository.reset_store()
    EventRepository.reset_store()
    ApprovalRepository.reset_store()


@pytest.mark.asyncio
async def test_discover_jobs_node():
    job1 = CanonicalJob(
        id=uuid4(),
        external_id="ext-test-1",
        source="TEST",
        source_url="https://example.com/jobs/1",
        title="Software Engineer",
        normalized_title="software engineer",
        company_name="TechCorp",
        normalized_company="techcorp",
        description="Build FastAPI backends",
        description_hash="hash-1",
        required_skills=["Python", "FastAPI"],
    )
    deps = CareerGraphDependencies(
        job_service=MockJobService(predefined_jobs=[job1]),
        run_repository=RunRepository,
        event_repository=EventRepository,
    )

    run_id = str(uuid4())
    profile_id = str(uuid4())
    user_id = str(uuid4())

    state = {
        "run_id": run_id,
        "request_id": "req-disc",
        "profile_id": profile_id,
        "user_id": user_id,
        "preferences": {"query": "Python", "limit": 5},
        "discovered_jobs": [],
        "events": [],
        "errors": [],
    }

    config = {"configurable": {"dependencies": deps}}
    out = await discover_jobs_node(state, config=config)

    assert len(out["discovered_jobs"]) == 1
    assert out["discovered_jobs"][0]["title"] == "Software Engineer"
    assert out["current_stage"] == "DISCOVERY"
    event_types = [e["event_type"] for e in out["events"]]
    assert "AGENT_STARTED" in event_types
    assert "JOB_DISCOVERY_STARTED" in event_types
    assert "JOB_DISCOVERY_COMPLETED" in event_types


@pytest.mark.asyncio
async def test_assess_trust_node():
    job_id = uuid4()
    job_dict = {
        "id": str(job_id),
        "title": "AI Researcher",
        "company_name": "Anthropic",
        "description": "LLM safety research",
    }
    deps = CareerGraphDependencies(
        trust_service=MockTrustService(default_score=98.0, default_risk="LOW"),
        run_repository=RunRepository,
        event_repository=EventRepository,
    )

    state = {
        "run_id": str(uuid4()),
        "profile_id": str(uuid4()),
        "user_id": str(uuid4()),
        "discovered_jobs": [job_dict],
        "trust_assessments": {},
        "events": [],
        "errors": [],
    }

    config = {"configurable": {"dependencies": deps}}
    out = await assess_trust_node(state, config=config)

    assert str(job_id) in out["trust_assessments"]
    assert out["trust_assessments"][str(job_id)]["trust_score"] == 98.0
    assert out["trust_assessments"][str(job_id)]["risk_level"] == "LOW"


@pytest.mark.asyncio
async def test_calculate_matches_node():
    job_id = uuid4()
    job_dict = {"id": str(job_id), "title": "Dev", "company_name": "A"}
    deps = CareerGraphDependencies(
        match_service=MockMatchService(default_score=88.5),
        run_repository=RunRepository,
        event_repository=EventRepository,
    )

    state = {
        "run_id": str(uuid4()),
        "profile_id": str(uuid4()),
        "user_id": str(uuid4()),
        "discovered_jobs": [job_dict],
        "profile_matches": {},
        "events": [],
        "errors": [],
    }

    config = {"configurable": {"dependencies": deps}}
    out = await calculate_matches_node(state, config=config)

    assert str(job_id) in out["profile_matches"]
    assert out["profile_matches"][str(job_id)]["overall_score"] == 88.5


@pytest.mark.asyncio
async def test_evaluate_decisions_node():
    job_id = uuid4()
    job_dict = {"id": str(job_id), "title": "Dev", "company_name": "A"}
    dec_service = MockDecisionService()
    dec_service.set_action(str(job_id), "AUTO_APPLY")

    deps = CareerGraphDependencies(
        decision_service=dec_service,
        run_repository=RunRepository,
        event_repository=EventRepository,
    )

    state = {
        "run_id": str(uuid4()),
        "profile_id": str(uuid4()),
        "user_id": str(uuid4()),
        "discovered_jobs": [job_dict],
        "decisions": {},
        "events": [],
        "errors": [],
    }

    config = {"configurable": {"dependencies": deps}}
    out = await evaluate_decisions_node(state, config=config)

    assert str(job_id) in out["decisions"]
    assert out["decisions"][str(job_id)]["action"] == "AUTO_APPLY"


@pytest.mark.asyncio
async def test_finalize_node_auto_apply():
    job_id = str(uuid4())
    state = {
        "run_id": str(uuid4()),
        "profile_id": str(uuid4()),
        "user_id": str(uuid4()),
        "decisions": {
            job_id: {
                "id": str(uuid4()),
                "action": "AUTO_APPLY",
                "overall_score": 93.0,
                "risk_level": "LOW",
            }
        },
        "resolved_approvals": [],
        "action_ready_jobs": [],
        "rejected_jobs": [],
        "events": [],
        "errors": [],
    }

    deps = CareerGraphDependencies(
        run_repository=RunRepository,
        event_repository=EventRepository,
    )
    config = {"configurable": {"dependencies": deps}}
    out = await finalize_node(state, config=config)

    assert out["status"] == "COMPLETED"
    assert len(out["action_ready_jobs"]) == 1
    assert out["action_ready_jobs"][0]["job_id"] == job_id
    assert len(out["rejected_jobs"]) == 0
