"""
CareerOS Phase 9.x — Deterministic Mocks for Graph Testing.

Provides zero-dependency, ₹0 offline mock services for:
- JobDiscoveryService
- TrustAssessmentService
- MatchService
- DecisionService
"""

from typing import Any
from uuid import UUID, uuid4

from apps.api.app.domain.decision.models import Decision
from apps.api.app.domain.job.models import CanonicalJob
from apps.api.app.domain.matching.models import MatchAgentOutput, MatchConfidence
from apps.api.app.domain.trust.models import ConfidenceLevel, RiskLevel, TrustAssessment
from apps.api.app.repositories.job_repository import JobRepository


class MockJobService:
    def __init__(self, predefined_jobs: list[CanonicalJob] | None = None):
        self.predefined_jobs = predefined_jobs or []
        for j in self.predefined_jobs:
            if isinstance(j, CanonicalJob):
                JobRepository._jobs[str(j.id)] = {
                    "id": j.id,
                    "external_id": j.external_id,
                    "source": j.source,
                    "source_url": j.source_url,
                    "title": j.title,
                    "normalized_title": j.normalized_title,
                    "company_name": j.company_name,
                    "normalized_company": j.normalized_company,
                    "description": j.description,
                    "description_hash": j.description_hash,
                    "location": j.location,
                    "work_mode": j.work_mode.value if hasattr(j.work_mode, "value") else str(j.work_mode),
                    "employment_type": j.employment_type.value if hasattr(j.employment_type, "value") else str(j.employment_type),
                    "salary_min": j.salary_min,
                    "salary_max": j.salary_max,
                    "salary_currency": j.salary_currency,
                    "application_url": j.application_url,
                    "posted_at": None,
                    "expires_at": None,
                    "required_skills": j.required_skills,
                    "preferred_skills": j.preferred_skills,
                    "experience_min": j.experience_min,
                    "ingestion_status": "NORMALIZED",
                    "normalization_version": "v1.0",
                    "is_active": True,
                    "metadata": j.metadata,
                    "embedding": None,
                    "imported_by_user_id": None,
                    "created_at": None,
                    "updated_at": None,
                }

    async def run_discovery(
        self,
        provider_names: list[str] | None = None,
        query: str | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        return {
            "results": self.predefined_jobs[:limit],
            "total_discovered": len(self.predefined_jobs[:limit]),
        }


class MockTrustService:
    def __init__(self, default_score: float = 95.0, default_risk: str = "LOW"):
        self.default_score = default_score
        self.default_risk = default_risk
        self.overrides: dict[str, tuple[float, str]] = {}

    def set_override(self, job_id: str, score: float, risk: str):
        self.overrides[job_id] = (score, risk)

    async def assess_job(self, job: CanonicalJob, force_refresh: bool = False) -> TrustAssessment:
        job_id_str = str(job.id)
        if job_id_str in self.overrides:
            score, risk = self.overrides[job_id_str]
        else:
            score, risk = self.default_score, self.default_risk

        return TrustAssessment(
            id=uuid4(),
            job_id=job.id,
            trust_score=score,
            risk_score=100.0 - score,
            risk_level=RiskLevel(risk),
            confidence=ConfidenceLevel.HIGH,
            explanation=f"Mock trust evaluation for {job.company_name}",
        )



class MockMatchService:
    def __init__(self, default_score: float = 92.0):
        self.default_score = default_score
        self.overrides: dict[str, float] = {}
        self.missing_skills_overrides: dict[str, list[str]] = {}

    def set_override(self, job_id: str, score: float, missing_skills: list[str] | None = None):
        self.overrides[job_id] = score
        if missing_skills is not None:
            self.missing_skills_overrides[job_id] = missing_skills

    async def calculate_match(
        self,
        profile_id: UUID,
        job_id: UUID,
        user_id: UUID,
        **kwargs,
    ) -> MatchAgentOutput:
        job_id_str = str(job_id)
        score = self.overrides.get(job_id_str, self.default_score)
        missing = self.missing_skills_overrides.get(job_id_str, [])

        return MatchAgentOutput(
            id=uuid4(),
            profile_id=profile_id,
            job_id=job_id,
            overall_score=score,
            semantic_score=score,
            skill_score=score,
            experience_score=score,
            location_score=score,
            preference_score=score,
            confidence=MatchConfidence.HIGH,
            matched_skills=["Python", "FastAPI"],
            missing_skills=missing,
            hard_constraints_passed=True,
            explanation=f"Deterministic mock match score {score}",
        )


class MockDecisionService:
    def __init__(self):
        self.overrides: dict[str, str] = {}  # job_id -> action

    def set_action(self, job_id: str, action: str):
        self.overrides[job_id] = action

    async def evaluate_decision(
        self,
        profile_id: UUID,
        job_id: UUID,
        user_id: UUID,
        policy: Any = None,
        application_context: Any = None,
        request_id: str = "internal",
    ) -> Decision:
        job_id_str = str(job_id)
        action = self.overrides.get(job_id_str, "AUTO_APPLY")
        risk = "HIGH" if action == "REJECT" and "high_risk" in job_id_str else "LOW"

        score = 92.0 if action == "AUTO_APPLY" else (82.0 if action == "USER_APPROVAL" else 45.0)

        return Decision(
            id=uuid4(),
            profile_id=profile_id,
            job_id=job_id,
            overall_score=score,
            match_score=score,
            trust_score=90.0 if risk != "HIGH" else 20.0,
            risk_level=risk,
            confidence="HIGH",
            action=action,
            reasons=[f"Mock decision policy outcome: {action}"],
            blocking_conditions=[] if action != "REJECT" else ["Low match or trust threshold"],
            eligible_for_auto_apply=(action == "AUTO_APPLY"),
            hard_constraints_passed=(action != "REJECT"),
            approval_required=(action == "USER_APPROVAL"),
            application_mode="USER_HANDOFF",
            policy_version="v1",
            decision_version="v1",
        )
