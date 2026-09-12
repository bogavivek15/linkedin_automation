"""
CareerOS Phase 15 — Professional Presence REST API Integration Tests.
"""

from uuid import uuid4

import pytest
from apps.api.app.domain.memory.models import CareerMemoryRecord
from apps.api.app.main import app
from apps.api.app.repositories.memory_repository import MemoryRepository
from apps.api.app.repositories.presence_repository import PresenceRepository
from httpx import ASGITransport, AsyncClient


@pytest.fixture(autouse=True)
def reset_presence_stores():
    PresenceRepository.reset_store()
    MemoryRepository.reset_store()


@pytest.mark.asyncio
async def test_presence_api_full_workflow():
    user_id = uuid4()
    profile_id = uuid4()

    # Seed a memory
    memory = CareerMemoryRecord(
        user_id=str(user_id),
        profile_id=str(profile_id),
        category="PROJECT",
        key="hybrid_search",
        content="Implemented hybrid semantic search engine using pgvector",
        provenance="Verified Git commit",
        confidence=0.95,
        verification_status="USER_CONFIRMED",
    )
    await MemoryRepository.save_memory(memory, user_id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {user_id}"}

        # 1. Generate ideas
        ideas_resp = await client.get(
            f"/api/v1/presence/ideas?profile_id={profile_id}",
            headers=headers,
        )
        assert ideas_resp.status_code == 200
        ideas = ideas_resp.json()["data"]
        assert len(ideas) >= 1

        # 2. Draft post from memory
        draft_resp = await client.post(
            "/api/v1/presence/draft",
            headers=headers,
            json={
                "profile_id": str(profile_id),
                "memory_id": str(memory.id),
                "content_type": "LINKEDIN_POST",
            },
        )
        assert draft_resp.status_code == 200
        post_data = draft_resp.json()["data"]
        post_id = post_data["id"]
        assert post_data["validation_status"] == "DRAFT"

        # 3. Approve post
        approve_resp = await client.post(
            f"/api/v1/presence/{post_id}/approve",
            headers=headers,
        )
        assert approve_resp.status_code == 200
        assert approve_resp.json()["data"]["validation_status"] == "APPROVED"

        # 4. User handoff publish
        handoff_resp = await client.post(
            f"/api/v1/presence/{post_id}/publish-handoff",
            headers=headers,
            json={"external_url": "https://linkedin.com/posts/candidate-post-1"},
        )
        assert handoff_resp.status_code == 200
        assert handoff_resp.json()["data"]["validation_status"] == "PUBLISHED"

        # 5. List posts
        list_resp = await client.get("/api/v1/presence", headers=headers)
        assert list_resp.status_code == 200
        assert len(list_resp.json()["data"]) == 1


@pytest.mark.asyncio
async def test_presence_api_rejects_ungrounded_post():
    user_id = uuid4()
    profile_id = uuid4()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {user_id}"}

        # Attempt to create custom post without grounding evidence
        resp = await client.post(
            "/api/v1/presence",
            headers=headers,
            json={
                "profile_id": str(profile_id),
                "title": "Unverified Post",
                "content_body": "This is a post without any evidence grounding citation.",
                "grounding_evidence_ids": [],  # Empty
            },
        )
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert detail["code"] == "UNGROUNDED_PRESENCE_CONTENT"


@pytest.mark.asyncio
async def test_presence_api_multi_tenant_isolation():
    user_a = uuid4()
    user_b = uuid4()
    profile_a = uuid4()

    # Seed memory for User A
    memory_a = CareerMemoryRecord(
        user_id=str(user_a),
        profile_id=str(profile_a),
        category="SKILL",
        key="async_python",
        content="FastAPI async engineering",
        provenance="Verified Git",
        confidence=0.9,
    )
    await MemoryRepository.save_memory(memory_a, user_a)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # User A drafts post
        res_a = await client.post(
            "/api/v1/presence/draft",
            headers={"Authorization": f"Bearer {user_a}"},
            json={"profile_id": str(profile_a), "memory_id": str(memory_a.id)},
        )
        post_id = res_a.json()["data"]["id"]

        # User B attempts to access User A's post
        get_b = await client.get(
            f"/api/v1/presence/{post_id}",
            headers={"Authorization": f"Bearer {user_b}"},
        )
        assert get_b.status_code == 404
