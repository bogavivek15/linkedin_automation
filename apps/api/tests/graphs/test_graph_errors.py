"""
CareerOS Phase 9.x — Graph Failure Recovery and Isolation Tests.
"""

from uuid import uuid4

import pytest
from apps.api.app.graphs.dependencies import CareerGraphDependencies
from apps.api.app.graphs.nodes.trust import assess_trust_node
from apps.api.app.repositories.event_repository import EventRepository
from apps.api.app.repositories.run_repository import RunRepository
from apps.api.tests.graphs.mocks import MockTrustService


class FailingTrustService(MockTrustService):
    async def assess_job(self, job, force_refresh=False):
        if "timeout" in job.company_name.lower():
            raise TimeoutError("External trust provider gateway timed out")
        return await super().assess_job(job, force_refresh=force_refresh)


@pytest.fixture(autouse=True)
def reset_stores():
    RunRepository.reset_store()
    EventRepository.reset_store()


@pytest.mark.asyncio
async def test_job_failure_isolation_in_trust_node():
    """
    Verify that if Job 2 times out, Job 1 and Job 3 still succeed,
    and the run records Job 2's error without crashing.
    """
    job1 = {"id": str(uuid4()), "title": "Dev 1", "company_name": "GoodCorp"}
    job2 = {"id": str(uuid4()), "title": "Dev 2", "company_name": "TimeoutCorp"}
    job3 = {"id": str(uuid4()), "title": "Dev 3", "company_name": "AnotherGoodCorp"}

    deps = CareerGraphDependencies(
        trust_service=FailingTrustService(),
        run_repository=RunRepository,
        event_repository=EventRepository,
    )

    state = {
        "run_id": str(uuid4()),
        "profile_id": str(uuid4()),
        "user_id": str(uuid4()),
        "discovered_jobs": [job1, job2, job3],
        "trust_assessments": {},
        "events": [],
        "errors": [],
    }

    config = {"configurable": {"dependencies": deps}}
    out = await assess_trust_node(state, config=config)

    assessments = out["trust_assessments"]
    assert len(assessments) == 3
    assert assessments[job1["id"]]["risk_level"] == "LOW"
    assert assessments[job2["id"]]["status"] == "FAILED"
    assert "timed out" in assessments[job2["id"]]["error"].lower()
    assert assessments[job3["id"]]["risk_level"] == "LOW"

    # Errors recorded
    assert len(out["errors"]) == 1
    assert out["errors"][0]["job_id"] == job2["id"]
