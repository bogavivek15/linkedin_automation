"""
CareerOS Phase 9.x — Event Repository.

Stores and queries structured AgentEvent records for observability.
Adheres to 021_career_events.sql with RLS user isolation.
"""

from typing import Any
from uuid import UUID

from apps.api.app.domain.graph.models import AgentEvent


class EventRepository:
    """
    Repository for storing and querying AgentEvents.
    """

    _events: list[dict[str, Any]] = []

    @classmethod
    def reset_store(cls) -> None:
        """Helper for test isolation."""
        cls._events.clear()

    @classmethod
    async def save_event(cls, event: AgentEvent, user_id: UUID) -> AgentEvent:
        """
        Record a structured event.
        """
        doc = {
            "event_id": event.event_id,
            "run_id": event.run_id,
            "profile_id": event.profile_id,
            "user_id": str(user_id),
            "job_id": event.job_id,
            "event_type": event.event_type,
            "agent_name": event.agent_name,
            "stage": event.stage,
            "status": event.status,
            "timestamp": event.timestamp,
            "metadata": event.metadata,
        }
        cls._events.append(doc)
        return event

    @classmethod
    async def get_events_for_run(
        cls,
        run_id: str,
        user_id: UUID,
    ) -> list[AgentEvent]:
        """
        Get all events for a run in chronological order, enforcing user isolation.
        """
        user_str = str(user_id)
        run_events = [
            e for e in cls._events
            if e.get("run_id") == str(run_id) and e.get("user_id") == user_str
        ]
        # Sort chronologically
        run_events.sort(key=lambda e: e.get("timestamp"))
        return [
            AgentEvent(**{k: v for k, v in e.items()})
            for e in run_events
        ]
