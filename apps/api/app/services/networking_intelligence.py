"""
CareerOS Phase 3 — Networking Intelligence Service.

Identifies high-signal professional connections for students based on:
- Target companies (e.g. Anthropic, Google DeepMind, NexusAI)
- Target roles (e.g. AI Systems Engineer, ML Engineer)
- Technical skill overlap (e.g. Python, LangGraph, pgvector, FastAPI)
- Shared projects & repository evidence

Core Invariant:
Zero spam. Never automatically send connection requests or messages.
All proposals require student authorization with explicit "Recommended because" reasons.
"""

from typing import Any
from uuid import UUID

from apps.api.app.domain.network.models import (
    AgentOutreachProposal,
    NetworkProfile,
)
from apps.api.app.repositories.network_repository import NetworkRepository
from apps.api.app.repositories.profile_repository import ProfileRepository


class NetworkingIntelligenceService:
    """
    Contextual matching engine for professional connections and evidence-grounded outreach.
    """

    @classmethod
    async def generate_connection_proposals(
        cls,
        user_id: UUID,
        profile_id: UUID | None = None,
        target_companies: list[str] | None = None,
        target_roles: list[str] | None = None,
        skills: list[str] | None = None,
    ) -> list[AgentOutreachProposal]:
        """
        Synthesize explainable, evidence-grounded connection proposals.
        """
        # 1. Load candidate profile context if not explicitly provided
        prof_id = profile_id or user_id
        candidate_skills: set[str] = set(s.lower() for s in (skills or []))
        user_companies: set[str] = set(c.lower() for c in (target_companies or []))
        user_roles: list[str] = list(target_roles or [])

        if not candidate_skills:
            try:
                cand = await ProfileRepository.build_candidate_profile(prof_id, user_id)
                if cand:
                    candidate_skills = set(s.name.lower() for s in cand.skills)
                    user_roles = user_roles or cand.target_roles or ["AI Engineer"]
            except Exception:
                pass

        if not user_roles:
            user_roles = ["AI Systems Engineer", "Machine Learning Engineer"]

        # Default target companies for students building autonomous agents
        if not user_companies:
            user_companies = {"anthropic", "google deepmind", "nexusai", "scale ai"}

        # 2. Fetch available network profiles
        network_profiles = await NetworkRepository.get_profiles()
        proposals: list[AgentOutreachProposal] = []

        for np in network_profiles:
            # Skip if already connected or pending
            if np.connection_status in ("CONNECTED", "PENDING"):
                continue

            company_norm = (np.company or "").lower()
            headline_lower = np.headline.lower()

            # Find shared skills
            profile_skills = set(s.lower() for s in np.skills)
            shared_skills = candidate_skills.intersection(profile_skills) if candidate_skills else set(["python", "fastapi"])
            shared_str = " + ".join(s.title() for s in list(shared_skills)[:3]) if shared_skills else "Python + AI Systems"

            is_target_company = any(tc in company_norm for tc in user_companies)
            is_relevant_role = any(kw in headline_lower for kw in ["engineer", "recruiter", "founder", "cto", "architect"])

            if not (is_target_company or is_relevant_role or np.is_target):
                continue

            # Calculate match score based on alignment
            score = 75
            if is_target_company:
                score += 15
            if shared_skills:
                score += min(10, len(shared_skills) * 4)
            score = min(98, score)

            # Generate explainable reason
            target_role_display = user_roles[0] if user_roles else "AI Engineer"
            target_company_display = np.company or "Target Organization"

            role_focus = "AI systems and autonomous agent workflows"
            if "inference" in np.about.lower() or "latency" in np.about.lower():
                role_focus = "high-performance inference systems"
            elif "recruiter" in np.headline.lower():
                role_focus = "university engineering talent and research internships"
            elif "alignment" in np.about.lower():
                role_focus = "agentic tool grounding and alignment"

            reasoning = (
                f"Recommended because:\n\n"
                f"• You are targeting {target_role_display} roles at {target_company_display}.\n"
                f"• {np.full_name} focuses on {role_focus} at {target_company_display}.\n"
                f"• Shared context: {shared_str}."
            )

            # Generate grounded outreach note
            if "recruiter" in np.headline.lower():
                note = (
                    f"Hi {np.full_name.split()[0]}, I saw your updates on {target_company_display}'s engineering hiring. "
                    f"I have been engineering autonomous career agent toolchains with pgvector and FastAPI, "
                    f"grounding every action against deterministic safety gates. Would value the opportunity to connect!"
                )
            else:
                note = (
                    f"Hi {np.full_name.split()[0]}, loved your work on {role_focus} at {target_company_display}. "
                    f"In my project CareerOS, I implemented an 8-gate deterministic policy engine and LangGraph state machine "
                    f"with verified evidence grounding. Would love to connect and follow your work!"
                )

            evidence_citations = [
                f"Shared Skills: {shared_str}",
                "CareerOS deterministic policy engine & LangGraph state machine",
            ]

            proposals.append(
                AgentOutreachProposal(
                    target_profile_id=np.id,
                    target_name=np.full_name,
                    target_headline=np.headline,
                    match_score=score,
                    proposed_note=note,
                    evidence_citations=evidence_citations,
                    gate_decision="NEEDS_APPROVAL",
                    reasoning=reasoning,
                )
            )

        # Sort proposals by match score descending
        proposals.sort(key=lambda p: p.match_score, reverse=True)
        return proposals
