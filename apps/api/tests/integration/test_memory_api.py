"""
CareerOS Phase 14 — Career Memory / Persistent Knowledge System REST API Integration Tests.
"""

from uuid import uuid4

import pytest
from apps.api.app.main import app
from apps.api.app.repositories.memory_repository import MemoryRepository
from httpx import ASGITransport, AsyncClient


@pytest.fixture(autouse=True)
def reset_memory_store():
    MemoryRepository.reset_store()


@pytest.mark.asyncio
async def test_memory_api_full_workflow():
    user_id = uuid4()
    profile_id = uuid4()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {user_id}"}

        # 1. Propose memory item as AI agent
        create_resp = await client.post(
            "/api/v1/memory",
            headers=headers,
            json={
                "profile_id": str(profile_id),
                "category": "PROJECT",
                "key": "distributed_rag",
                "content": "Engineered hybrid vector search using Supabase pgvector.",
                "provenance": "Extracted from GitHub repo commit e84f9",
                "confidence": 0.95,
                "actor": "AI_AGENT",
                "evidence_provided": True,
            },
        )
        assert create_resp.status_code == 200
        data = create_resp.json()["data"]
        memory_id = data["id"]
        assert data["verification_status"] == "EVIDENCE_VALIDATED"

        # 2. Get specific memory item
        get_resp = await client.get(f"/api/v1/memory/{memory_id}", headers=headers)
        assert get_resp.status_code == 200
        assert get_resp.json()["data"]["key"] == "distributed_rag"

        # 3. Confirm memory item by candidate
        confirm_resp = await client.post(
            f"/api/v1/memory/{memory_id}/confirm",
            headers=headers,
        )
        assert confirm_resp.status_code == 200
        assert confirm_resp.json()["data"]["verification_status"] == "USER_CONFIRMED"

        # 4. Contextual retrieval for application
        app_ctx_resp = await client.get(
            f"/api/v1/memory/retrieve/application?profile_id={profile_id}",
            headers=headers,
        )
        assert app_ctx_resp.status_code == 200
        app_data = app_ctx_resp.json()["data"]
        assert len(app_data["projects"]) == 1
        assert app_data["projects"][0]["key"] == "distributed_rag"

        # 5. Delete memory
        del_resp = await client.delete(f"/api/v1/memory/{memory_id}", headers=headers)
        assert del_resp.status_code == 200
        assert del_resp.json()["data"]["deleted"] is True


@pytest.mark.asyncio
async def test_memory_api_prohibits_ai_direct_authoritative():
    user_id = uuid4()
    profile_id = uuid4()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {user_id}"}

        # Attempt authoritative write by AI
        resp = await client.post(
            "/api/v1/memory",
            headers=headers,
            json={
                "profile_id": str(profile_id),
                "category": "EXPERIENCE",
                "key": "lead_architect",
                "content": "Senior Engineering Lead",
                "provenance": "No evidence provided",
                "proposed_status": "AUTHORITATIVE",
                "actor": "AI_AGENT",
                "evidence_provided": False,
            },
        )
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert detail["code"] == "DIRECT_AUTHORITATIVE_WRITE_PROHIBITED"


@pytest.mark.asyncio
async def test_memory_api_multi_tenant_isolation():
    user_a = uuid4()
    user_b = uuid4()
    profile_a = uuid4()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # User A creates memory
        res = await client.post(
            "/api/v1/memory",
            headers={"Authorization": f"Bearer {user_a}"},
            json={
                "profile_id": str(profile_a),
                "category": "SKILL",
                "key": "secret_skill",
                "content": "Proprietary research skill",
                "provenance": "Confidential",
                "actor": "USER",
            },
        )
        mem_id = res.json()["data"]["id"]

        # User B attempts to access User A's memory
        get_b = await client.get(
            f"/api/v1/memory/{mem_id}",
            headers={"Authorization": f"Bearer {user_b}"},
        )
        assert get_b.status_code == 404

        # User B attempts to delete User A's memory
        del_b = await client.delete(
            f"/api/v1/memory/{mem_id}",
            headers={"Authorization": f"Bearer {user_b}"},
        )
        assert del_b.status_code == 404
