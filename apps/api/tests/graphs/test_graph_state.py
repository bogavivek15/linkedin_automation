"""
CareerOS Phase 9.x — Graph State Tests.
"""

from uuid import uuid4

from apps.api.app.graphs.state import CareerGraphState


def test_valid_initial_state():
    run_id = str(uuid4())
    profile_id = str(uuid4())
    user_id = str(uuid4())

    state: CareerGraphState = {
        "run_id": run_id,
        "request_id": "req-123",
        "profile_id": profile_id,
        "user_id": user_id,
        "target_roles": ["AI Engineer"],
        "preferences": {"query": "python"},
        "discovered_jobs": [],
        "current_job_id": None,
        "trust_assessments": {},
        "profile_matches": {},
        "decisions": {},
        "pending_approvals": [],
        "action_ready_jobs": [],
        "rejected_jobs": [],
        "resolved_approvals": [],
        "current_stage": "INIT",
        "status": "RUNNING",
        "errors": [],
        "events": [],
        "graph_name": "career_intelligence",
        "graph_version": "v1",
    }

    assert state["run_id"] == run_id
    assert state["status"] == "RUNNING"
    assert state["current_stage"] == "INIT"
    assert len(state["discovered_jobs"]) == 0
    assert len(state["events"]) == 0


def test_state_transitions_and_accumulation():
    state: CareerGraphState = {
        "run_id": str(uuid4()),
        "request_id": "req-1",
        "profile_id": str(uuid4()),
        "user_id": str(uuid4()),
        "discovered_jobs": [{"id": "job-1", "title": "Dev"}],
        "events": [{"event_type": "RUN_STARTED"}],
        "current_stage": "DISCOVERY",
    }

    # Simulate accumulation
    state["discovered_jobs"].append({"id": "job-2", "title": "Lead"})
    state["events"].append({"event_type": "JOB_DISCOVERY_COMPLETED"})
    state["current_stage"] = "TRUST"

    assert len(state["discovered_jobs"]) == 2
    assert len(state["events"]) == 2
    assert state["current_stage"] == "TRUST"


def test_no_sensitive_fields_in_state():
    sensitive_keys = {
        "password",
        "token",
        "access_token",
        "jwt",
        "secret",
        "service_role_key",
        "supabase_service_role_key",
        "cookie",
    }

    state: CareerGraphState = {
        "run_id": str(uuid4()),
        "request_id": "req-1",
        "profile_id": str(uuid4()),
        "user_id": str(uuid4()),
        "target_roles": ["Backend Developer"],
        "preferences": {},
        "discovered_jobs": [],
        "trust_assessments": {},
        "profile_matches": {},
        "decisions": {},
        "pending_approvals": [],
        "current_stage": "INIT",
        "status": "RUNNING",
        "errors": [],
        "events": [],
        "graph_name": "career_intelligence",
        "graph_version": "v1",
    }

    for key in state:
        assert key.lower() not in sensitive_keys, f"Found sensitive key in graph state: {key}"
