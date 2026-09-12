"""
CareerOS Phase 16 — Agent Registry & Orchestration REST API Integration Tests.
"""

from uuid import uuid4

import pytest
from apps.api.app.main import app
from apps.api.app.repositories.agent_repository import AgentRepository
from httpx import ASGITransport, AsyncClient


@pytest.fixture(autouse=True)
def reset_agent_store():
    AgentRepository.reset_store()


@pytest.mark.asyncio
async def test_agents_api_registry_inspection():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/agents")
        assert resp.status_code == 200
        agents = resp.json()["data"]
        assert len(agents) == 8

        # Get specific agent
        spec_resp = await client.get("/api/v1/agents/Trust & Safety Agent")
        assert spec_resp.status_code == 200
        assert spec_resp.json()["data"]["category"] == "SECURITY"


@pytest.mark.asyncio
async def test_agents_api_launch_and_telemetry_flow():
    user_id = uuid4()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {user_id}"}

        # 1. Launch orchestrated multi-agent run
        launch_resp = await client.post(
            "/api/v1/agents/launch",
            headers=headers,
            json={"target_role": "AI Engineer", "query": "python async"},
        )
        assert launch_resp.status_code == 200
        run_data = launch_resp.json()["data"]
        run_id = run_data["id"]
        assert run_data["status"] == "COMPLETED"
        assert len(run_data["events"]) == 5  # 5 observable pipeline events

        # 2. Query run details
        get_resp = await client.get(f"/api/v1/agents/runs/{run_id}", headers=headers)
        assert get_resp.status_code == 200
        assert get_resp.json()["data"]["id"] == run_id

        # 3. List runs
        list_resp = await client.get("/api/v1/agents/runs", headers=headers)
        assert list_resp.status_code == 200
        assert len(list_resp.json()["data"]) >= 1


@pytest.mark.asyncio
async def test_agents_api_multi_tenant_isolation():
    user_a = uuid4()
    user_b = uuid4()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # User A launches run
        res_a = await client.post(
            "/api/v1/agents/launch",
            headers={"Authorization": f"Bearer {user_a}"},
            json={"target_role": "Staff Engineer"},
        )
        run_id = res_a.json()["data"]["id"]

        # User B cannot access User A's run
        get_b = await client.get(
            f"/api/v1/agents/runs/{run_id}",
            headers={"Authorization": f"Bearer {user_b}"},
        )
        assert get_b.status_code == 404
