"""
CareerOS Phase 16 — Agent Registry & Run Repository.

Persistence layer for agent registry state, orchestration runs, and
observable event timelines. Multi-tenant isolated.
"""

from typing import Any
from uuid import UUID

from apps.api.app.domain.agents.models import (
    AgentRegistryEntry,
    AgentRunRecord,
    AgentStatus,
    ObservableAgentEvent,
)
from apps.api.app.domain.agents.registry import CANONICAL_AGENTS


class AgentRepository:
    """
    Repository for agent registry, runs, and observable events.
    """

    _registry: dict[str, AgentRegistryEntry] = {
        agent.agent_name: agent.model_copy(deep=True) for agent in CANONICAL_AGENTS
    }
    _runs: dict[str, dict[str, Any]] = {}
    _content_generations: dict[str, dict[str, Any]] = {}
    _platform_posts: dict[str, dict[str, Any]] = {}

    @classmethod
    def reset_store(cls) -> None:
        """Helper for test isolation."""
        cls._registry = {
            agent.agent_name: agent.model_copy(deep=True) for agent in CANONICAL_AGENTS
        }
        cls._runs.clear()
        cls._content_generations.clear()
        cls._platform_posts.clear()

    @classmethod
    async def list_agents(cls) -> list[AgentRegistryEntry]:
        return list(cls._registry.values())

    @classmethod
    async def get_agent(cls, agent_name: str) -> AgentRegistryEntry | None:
        return cls._registry.get(agent_name)

    @classmethod
    async def update_agent_status(
        cls,
        agent_name: str,
        status: AgentStatus,
    ) -> AgentRegistryEntry | None:
        agent = cls._registry.get(agent_name)
        if not agent:
            return None
        agent.status = status
        return agent

    @classmethod
    async def save_run(
        cls,
        run: AgentRunRecord,
        user_id: UUID,
    ) -> AgentRunRecord:
        run_id = str(run.id)
        user_str = str(user_id)

        doc = {
            "id": run_id,
            "request_id": run.request_id,
            "user_id": user_str,
            "primary_agent": run.primary_agent,
            "status": run.status,
            "duration_ms": run.duration_ms,
            "inputs_metadata": run.inputs_metadata,
            "outputs_metadata": run.outputs_metadata,
            "errors": run.errors,
            "events": run.events,
            "started_at": run.started_at,
            "completed_at": run.completed_at,
            "_raw_model": run,
        }
        cls._runs[run_id] = doc
        return run

    @classmethod
    async def get_run(
        cls,
        run_id: str,
        user_id: UUID,
    ) -> AgentRunRecord | None:
        doc = cls._runs.get(str(run_id))
        if not doc or doc["user_id"] != str(user_id):
            return None
        return doc["_raw_model"]

    @classmethod
    async def list_runs(
        cls,
        user_id: UUID,
        limit: int = 20,
    ) -> list[AgentRunRecord]:
        user_str = str(user_id)
        results: list[AgentRunRecord] = []
        for doc in cls._runs.values():
            if doc["user_id"] == user_str:
                results.append(doc["_raw_model"])
        return sorted(results, key=lambda x: x.started_at, reverse=True)[:limit]

    @classmethod
    async def append_event(
        cls,
        run_id: str,
        event: ObservableAgentEvent,
        user_id: UUID,
    ) -> bool:
        doc = cls._runs.get(str(run_id))
        if not doc or doc["user_id"] != str(user_id):
            return False
        run: AgentRunRecord = doc["_raw_model"]
        run.events.append(event)
        return True

    @classmethod
    async def save_content_generation(cls, generation: dict) -> dict:
        cls._content_generations[generation["id"]] = generation
        return generation

    @classmethod
    async def get_pending_approvals(cls, user_id: UUID) -> list[dict]:
        user_str = str(user_id)
        return [
            doc for doc in cls._content_generations.values()
            if doc["user_id"] == user_str and doc["status"] == "PENDING"
        ]
        
    @classmethod
    async def get_content_generation(cls, gen_id: str, user_id: UUID) -> dict | None:
        doc = cls._content_generations.get(gen_id)
        if not doc or doc["user_id"] != str(user_id):
            return None
        return doc
        
    @classmethod
    async def update_content_status(cls, gen_id: str, status: str, user_id: UUID) -> dict | None:
        doc = await cls.get_content_generation(gen_id, user_id)
        if not doc:
            return None
        doc["status"] = status
        return doc
        
    @classmethod
    async def save_platform_post(cls, post: dict) -> dict:
        cls._platform_posts[post["id"]] = post
        return post
