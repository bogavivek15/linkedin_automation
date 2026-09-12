"""
CareerOS Phase 9.x — Graph Checkpoint Tests.
"""

from uuid import uuid4

import pytest
from apps.api.app.graphs.checkpoint import (
    InMemoryCheckpointStore,
    PersistentCheckpointStore,
)


@pytest.mark.asyncio
async def test_in_memory_checkpoint_store():
    store = InMemoryCheckpointStore()
    thread_id = str(uuid4())
    snapshot = {"run_id": thread_id, "current_stage": "APPROVAL", "pending_approvals": [1, 2]}

    await store.save(thread_id, snapshot)
    loaded = await store.load(thread_id)

    assert loaded is not None
    assert loaded["run_id"] == thread_id
    assert loaded["current_stage"] == "APPROVAL"

    # Non-existent
    missing = await store.load("unknown-thread")
    assert missing is None


@pytest.mark.asyncio
async def test_persistent_checkpoint_store():
    store = PersistentCheckpointStore()
    thread_id = str(uuid4())
    snapshot = {"run_id": thread_id, "status": "WAITING_FOR_APPROVAL"}

    await store.save(thread_id, snapshot)
    loaded = await store.load(thread_id)

    assert loaded is not None
    assert loaded["status"] == "WAITING_FOR_APPROVAL"
