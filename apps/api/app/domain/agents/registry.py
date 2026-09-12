"""
CareerOS Phase 16 — Canonical Agent Registry.

Instantiates the 3 core autonomous agents and the orchestrator.
"""

from datetime import datetime, timezone

from apps.api.app.domain.agents.models import AgentRegistryEntry

CANONICAL_AGENTS: list[AgentRegistryEntry] = [
    AgentRegistryEntry(
        agent_name="Orchestrator Agent",
        agent_version="2.0.0",
        category="ORCHESTRATION",
        capabilities=["graph_dispatch", "state_transition_gate", "pipeline_coordination"],
        permissions=["execute_graph", "emit_audit_event"],
        status="ACTIVE",
        last_run_at=datetime.now(timezone.utc),
        metadata={"engine": "LangGraph", "timeout_seconds": 120},
    ),
    AgentRegistryEntry(
        agent_name="Job Matcher Agent",
        agent_version="1.0.0",
        category="DISCOVERY",
        capabilities=["resume_parsing", "internal_job_search", "skill_matching"],
        permissions=["read_resumes", "read_internal_jobs", "write_canonical_jobs"],
        status="ACTIVE",
        last_run_at=datetime.now(timezone.utc),
        metadata={"sources": ["InternalDB"], "batch_size": 50},
    ),
    AgentRegistryEntry(
        agent_name="Trust & Safety Agent",
        agent_version="2.1.0",
        category="SECURITY",
        capabilities=["scam_detection", "company_verification_via_gemini"],
        permissions=["read_jobs", "write_trust_assessments", "block_high_risk"],
        status="ACTIVE",
        last_run_at=datetime.now(timezone.utc),
        metadata={"ssrf_protection": True, "strict_policy_eval": True},
    ),
    AgentRegistryEntry(
        agent_name="Auto Apply Agent",
        agent_version="1.0.0",
        category="EXECUTION_PREP",
        capabilities=["form_filling", "application_submission"],
        permissions=["read_jobs", "read_resumes", "write_application_status"],
        status="ACTIVE",
        last_run_at=datetime.now(timezone.utc),
        metadata={"require_approval": False},
    ),
]
