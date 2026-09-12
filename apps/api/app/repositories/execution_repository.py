"""
CareerOS Phase 11 — Application Execution Repository.

Persistence layer for controlled executions and execution audit events.
Enforces multi-tenant user isolation and idempotency matching 024_executions.sql.
"""

from typing import Any
from uuid import UUID

from apps.api.app.domain.execution.models import (
    ApplicationExecution,
    ExecutionAuditEvent,
)


class ExecutionRepository:
    """
    Repository for persisting and querying ApplicationExecution records.
    Provides strict user isolation and idempotency per idempotency_key.
    """

    _executions: dict[str, dict[str, Any]] = {}  # execution_id -> dict
    _index_idempotency: dict[str, str] = {}      # f"{user_id}:{idempotency_key}" -> execution_id
    _index_package: dict[str, str] = {}          # f"{user_id}:{package_id}" -> latest execution_id
    _audit_events: dict[str, list[dict[str, Any]]] = {}  # execution_id -> list[event_dict]

    @classmethod
    def reset_store(cls) -> None:
        """Helper for test isolation."""
        cls._executions.clear()
        cls._index_idempotency.clear()
        cls._index_package.clear()
        cls._audit_events.clear()

    @classmethod
    async def save_execution(
        cls,
        execution: ApplicationExecution,
        user_id: UUID,
    ) -> ApplicationExecution:
        """
        Save or update an ApplicationExecution with user isolation.
        """
        exec_id = str(execution.id)
        user_str = str(user_id)
        idemp_key = f"{user_str}:{execution.idempotency_key}"
        pkg_key = f"{user_str}:{execution.application_package_id}"

        doc = {
            "id": exec_id,
            "application_package_id": str(execution.application_package_id),
            "user_id": user_str,
            "profile_id": str(execution.profile_id),
            "job_id": str(execution.job_id),
            "decision_id": str(execution.decision_id) if execution.decision_id else None,
            "execution_mode": execution.execution_mode,
            "status": execution.status,
            "idempotency_key": execution.idempotency_key,
            "receipt": execution.receipt.model_dump(mode="json") if execution.receipt else {},
            "handoff_details": execution.handoff_details.model_dump(mode="json") if execution.handoff_details else {},
            "safety_gate_results": execution.safety_gate_results.model_dump(mode="json") if execution.safety_gate_results else {},
            "failure_reason": execution.failure_reason,
            "notes": execution.notes,
            "submitted_at": execution.submitted_at,
            "verified_at": execution.verified_at,
            "created_at": execution.created_at,
            "updated_at": execution.updated_at,
            "_raw_model": execution,
        }

        cls._executions[exec_id] = doc
        cls._index_idempotency[idemp_key] = exec_id
        cls._index_package[pkg_key] = exec_id
        return execution

    @classmethod
    async def get_execution(
        cls,
        execution_id: UUID | str,
        user_id: UUID,
    ) -> ApplicationExecution | None:
        """
        Retrieve single execution with user isolation.
        """
        doc = cls._executions.get(str(execution_id))
        if not doc or doc["user_id"] != str(user_id):
            return None
        return doc["_raw_model"]

    @classmethod
    async def get_by_idempotency_key(
        cls,
        idempotency_key: str,
        user_id: UUID,
    ) -> ApplicationExecution | None:
        """
        Look up execution by idempotency key for the authenticated user.
        """
        key = f"{user_id}:{idempotency_key}"
        exec_id = cls._index_idempotency.get(key)
        if not exec_id:
            return None
        return await cls.get_execution(exec_id, user_id)

    @classmethod
    async def get_by_package_id(
        cls,
        package_id: UUID | str,
        user_id: UUID,
    ) -> ApplicationExecution | None:
        """
        Retrieve latest execution associated with an application package.
        """
        key = f"{user_id}:{package_id}"
        exec_id = cls._index_package.get(key)
        if not exec_id:
            return None
        return await cls.get_execution(exec_id, user_id)

    @classmethod
    async def list_executions(
        cls,
        user_id: UUID,
        status: str | None = None,
    ) -> list[ApplicationExecution]:
        """
        List all executions for authenticated user, optionally filtered by status.
        """
        user_str = str(user_id)
        results: list[ApplicationExecution] = []
        for doc in cls._executions.values():
            if doc["user_id"] == user_str:
                if status and doc["status"] != status:
                    continue
                results.append(doc["_raw_model"])
        return sorted(results, key=lambda x: x.created_at, reverse=True)

    @classmethod
    async def save_audit_event(
        cls,
        event: ExecutionAuditEvent,
        user_id: UUID,
    ) -> ExecutionAuditEvent:
        """
        Save an execution audit event with user isolation.
        """
        exec_id = str(event.execution_id)
        if exec_id not in cls._audit_events:
            cls._audit_events[exec_id] = []

        cls._audit_events[exec_id].append({
            "id": str(event.id),
            "execution_id": exec_id,
            "user_id": str(user_id),
            "event_type": event.event_type,
            "actor": event.actor,
            "payload": event.payload,
            "created_at": event.created_at,
            "_raw_model": event,
        })
        return event

    @classmethod
    async def get_audit_events(
        cls,
        execution_id: UUID | str,
        user_id: UUID,
    ) -> list[ExecutionAuditEvent]:
        """
        Retrieve all audit events for an execution, ensuring user isolation.
        """
        exec_id = str(execution_id)
        doc = cls._executions.get(exec_id)
        if not doc or doc["user_id"] != str(user_id):
            return []

        raw_events = cls._audit_events.get(exec_id, [])
        return [e["_raw_model"] for e in raw_events]
