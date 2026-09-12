"""
CareerOS Phase 9.x — Graph Routing Tests.
"""

from uuid import uuid4

from apps.api.app.graphs.routing import route_after_decision
from apps.api.app.graphs.state import CareerGraphState


def test_routing_auto_apply_routes_to_finalize():
    job_id = str(uuid4())
    state: CareerGraphState = {
        "decisions": {
            job_id: {
                "action": "AUTO_APPLY",
                "risk_level": "LOW",
                "overall_score": 94.0,
            }
        },
        "resolved_approvals": [],
    }

    route = route_after_decision(state)
    assert route == "finalize"


def test_routing_user_approval_routes_to_approval_gate():
    job_id = str(uuid4())
    state: CareerGraphState = {
        "decisions": {
            job_id: {
                "action": "USER_APPROVAL",
                "risk_level": "LOW",
                "overall_score": 82.0,
            }
        },
        "resolved_approvals": [],
    }

    route = route_after_decision(state)
    assert route == "approval_gate"


def test_routing_high_risk_never_routes_to_approval_gate():
    job_id = str(uuid4())
    state: CareerGraphState = {
        "decisions": {
            job_id: {
                "action": "REJECT",
                "risk_level": "HIGH",
                "overall_score": 30.0,
            }
        },
        "resolved_approvals": [],
    }

    route = route_after_decision(state)
    assert route == "finalize"


def test_routing_resolved_approval_routes_to_finalize():
    job_id = str(uuid4())
    state: CareerGraphState = {
        "decisions": {
            job_id: {
                "action": "USER_APPROVAL",
                "risk_level": "LOW",
                "overall_score": 84.0,
            }
        },
        "resolved_approvals": [{"job_id": job_id, "status": "APPROVED"}],
    }

    route = route_after_decision(state)
    assert route == "finalize"
