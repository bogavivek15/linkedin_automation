"""
CareerOS Phase 9.x — Run Repository.

Transactional in-memory store for Career Intelligence workflow runs.
Adheres to 020_career_runs.sql with strict RLS user isolation.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from apps.api.app.domain.graph.models import CareerRun, RunStatus


class RunRepository:
    """
    Repository for storing and querying CareerRun records.
    """

    _runs: dict[str, dict[str, Any]] = {}  # run_id_str -> dict
    _index_request_user: dict[str, str] = {}  # f"{user_id}:{request_id}" -> run_id_str

    @classmethod
    def reset_store(cls) -> None:
        """Helper for test isolation."""
        cls._runs.clear()
        cls._index_request_user.clear()

    @classmethod
    async def save_run(cls, run: CareerRun, user_id: UUID) -> CareerRun:
        """
        Save or upsert a career run.
        """
        run_id_str = str(run.id)
        now = datetime.now(timezone.utc)
        req_key = f"{user_id}:{run.request_id}"

        doc = {
            "id": run.id,
            "profile_id": run.profile_id,
            "user_id": user_id,
            "request_id": run.request_id,
            "graph_name": run.graph_name,
            "graph_version": run.graph_version,
            "status": run.status,
            "current_stage": run.current_stage,
            "started_at": run.started_at,
            "completed_at": run.completed_at,
            "error": run.error,
            "metadata": run.metadata,
            "state_snapshot": run.state_snapshot,
            "created_at": now,
            "updated_at": now,
        }

        cls._runs[run_id_str] = doc
        cls._index_request_user[req_key] = run_id_str
        return run

    @classmethod
    async def get_run(cls, run_id: UUID, user_id: UUID) -> CareerRun | None:
        """
        Get run by ID enforcing user isolation.
        """
        doc = cls._runs.get(str(run_id))
        if not doc or doc.get("user_id") != user_id:
            return None
        return CareerRun(**{k: v for k, v in doc.items() if k not in ("created_at", "updated_at")})

    @classmethod
    async def find_by_request_id(cls, request_id: str, user_id: UUID) -> CareerRun | None:
        """
        Look up run by idempotency request_id for user.
        """
        req_key = f"{user_id}:{request_id}"
        run_id_str = cls._index_request_user.get(req_key)
        if not run_id_str:
            return None
        return await cls.get_run(UUID(run_id_str), user_id)

    @classmethod
    async def update_run(
        cls,
        run_id: UUID,
        user_id: UUID,
        status: str | None = None,
        current_stage: str | None = None,
        error: str | None = None,
        metadata_update: dict[str, Any] | None = None,
        state_snapshot: dict[str, Any] | None = None,
        completed_at: datetime | None = None,
    ) -> CareerRun | None:
        """
        Update run status, stage, metadata, and snapshot.
        """
        run_id_str = str(run_id)
        doc = cls._runs.get(run_id_str)
        if not doc or doc.get("user_id") != user_id:
            return None

        now = datetime.now(timezone.utc)
        if status is not None:
            doc["status"] = status
        if current_stage is not None:
            doc["current_stage"] = current_stage
        if error is not None:
            doc["error"] = error
        if metadata_update is not None:
            doc["metadata"] = {**doc.get("metadata", {}), **metadata_update}
        if state_snapshot is not None:
            doc["state_snapshot"] = state_snapshot
        if completed_at is not None:
            doc["completed_at"] = completed_at
        elif status in (RunStatus.COMPLETED.value, RunStatus.FAILED.value, RunStatus.CANCELLED.value) and not doc.get("completed_at"):
            doc["completed_at"] = now

        doc["updated_at"] = now
        return CareerRun(**{k: v for k, v in doc.items() if k not in ("created_at", "updated_at")})

    @classmethod
    async def cancel_run(cls, run_id: UUID, user_id: UUID) -> CareerRun | None:
        """
        Safely cancel a run.
        """
        return await cls.update_run(
            run_id=run_id,
            user_id=user_id,
            status=RunStatus.CANCELLED.value,
            error="Run cancelled by user",
            completed_at=datetime.now(timezone.utc),
        )

    @classmethod
    async def list_runs_for_user(
        cls,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[CareerRun]:
        """
        List runs for authenticated user, sorted by started_at descending.
        """
        user_runs = [d for d in cls._runs.values() if d.get("user_id") == user_id]
        user_runs.sort(key=lambda d: d.get("started_at", datetime.min), reverse=True)
        sliced = user_runs[offset : offset + limit]
        return [CareerRun(**{k: v for k, v in d.items() if k not in ("created_at", "updated_at")}) for d in sliced]
