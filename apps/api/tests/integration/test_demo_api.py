"""
CareerOS Phase 21 — Demo API Integration Tests.

Validates the end-to-end demo scenario:
- Student Profile & verified Career Memory
- Opportunity A (Stripe, 92% Match, 94% Trust) -> Approved, Prepared, Handoff
- Opportunity B (Apex Global, 96% Match, 18% Trust Scam) -> Blocked by Gate 1
- High Match ≠ Automatically Safe validation
- Multi-agent observable feed
"""

import pytest
from apps.api.app.main import app
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_get_demo_scenario():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/demo/scenario")

    assert response.status_code == 200
    data = response.json()

    assert data["scenario_name"] == "CareerOS Hackathon End-to-End Demo"
    assert "candidate" in data
    assert data["candidate"]["name"] == "Alex Rivera"

    # Verify Career Memory
    assert len(data["career_memory"]) >= 5
    assert all(m["confidence"] >= 0.9 for m in data["career_memory"])

    # Verify Opportunity A (Stripe)
    opp_a = data["opportunity_a"]
    assert opp_a["company_name"] == "Stripe"
    assert opp_a["match"]["overall_score"] >= 90.0
    assert opp_a["trust"]["trust_score"] >= 80.0
    assert opp_a["trust"]["risk_level"] == "LOW"
    assert opp_a["decision"]["action"] in ("PREPARE_APPLICATION", "AUTO_APPLY", "USER_APPROVAL")
    assert opp_a["application_package"]["status"] == "APPROVED"
    assert opp_a["execution"]["mode"] == "USER_HANDOFF"
    assert opp_a["execution"]["user_assertion"]["marked_as_submitted"] is True
    assert opp_a["lifecycle"]["current_status"] == "INTERVIEW"

    # Verify Opportunity B (Apex Global Staffing Scam)
    opp_b = data["opportunity_b"]
    assert opp_b["company_name"] == "Apex Global Staffing"
    assert opp_b["match"]["overall_score"] >= 95.0  # High match deceptive keyword match
    assert opp_b["trust"]["trust_score"] < 30.0  # Scam
    assert opp_b["trust"]["risk_level"] == "HIGH"
    assert opp_b["decision"]["action"] in ("BLOCK_APPLICATION", "REJECT")
    assert opp_b["application_package"]["status"] == "NOT_PREPARED"

    # Verify Crucial Contrast: High Match != Automatically Safe
    assert opp_b["match"]["overall_score"] > opp_a["match"]["overall_score"]
    assert opp_a["trust"]["trust_score"] > opp_b["trust"]["trust_score"]
    assert opp_b["decision"]["action"] in ("BLOCK_APPLICATION", "REJECT")

    # Verify Multi-Agent Feed
    assert len(data["agent_runs"]) >= 8


@pytest.mark.asyncio
async def test_seed_demo_scenario():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/demo/seed")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SEEDED"
    assert "scenario" in data
