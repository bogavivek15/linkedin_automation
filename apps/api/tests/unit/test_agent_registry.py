"""
Unit tests for CareerOS Phase 16 — Agent Registry & Canonical Definitions.
"""

from apps.api.app.domain.agents.registry import CANONICAL_AGENTS


def test_canonical_agent_registry_contains_eight_core_agents():
    """
    Verifies that the canonical registry contains the 8 core agents required by CareerOS:
    1. Orchestrator Agent
    2. Opportunity Agent
    3. Trust & Safety Agent
    4. Profile Agent
    5. Application Agent
    6. Presence Agent
    7. Learning Agent
    8. Memory Agent
    """
    assert len(CANONICAL_AGENTS) == 8
    names = {a.agent_name for a in CANONICAL_AGENTS}
    expected = {
        "Orchestrator Agent",
        "Opportunity Agent",
        "Trust & Safety Agent",
        "Profile Agent",
        "Application Agent",
        "Presence Agent",
        "Learning Agent",
        "Memory Agent",
    }
    assert names == expected


def test_agents_have_explicit_capabilities_and_permissions():
    """
    Each autonomous agent must declare formal capabilities and permissions.
    """
    for agent in CANONICAL_AGENTS:
        assert len(agent.capabilities) >= 1
        assert len(agent.permissions) >= 1
        assert agent.status in ("ACTIVE", "IDLE", "STANDBY", "MAINTENANCE")
