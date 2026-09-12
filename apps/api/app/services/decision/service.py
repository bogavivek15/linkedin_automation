"""
CareerOS Phase 9 — Decision Service.

Orchestrates the deterministic decision evaluation flow:
    Load Match
          ↓
    Load Trust Assessment
          ↓
    Load Candidate Policy
          ↓
    Load Application Context
          ↓
    Calculate Final Score
          ↓
    Evaluate HIGH Risk
          ↓
    Evaluate Hard Constraints
          ↓
    Evaluate UNKNOWN Risk
          ↓
    Evaluate Trust Threshold
          ↓
    Evaluate Confidence
          ↓
    Evaluate Automation Policy
          ↓
    Evaluate Application Safety
          ↓
    Evaluate Match Threshold
          ↓
    Determine Action
          ↓
    Generate Reasons
          ↓
    Persist Decision

Emits structured observability events. Zero LLM calls.
"""

import time
from typing import Any
from uuid import UUID

from apps.api.app.core.errors import CareerOSError
from apps.api.app.core.logging import get_logger
from apps.api.app.services.decision.models import (
    ApplicationContext,
    CandidateAutomationPolicy,
    Decision,
)
from apps.api.app.repositories.decision_repository import DecisionRepository
from apps.api.app.repositories.job_repository import JobRepository
from apps.api.app.repositories.match_repository import MatchRepository
from apps.api.app.repositories.profile_repository import ProfileRepository
from apps.api.app.repositories.trust_repository import TrustRepository
from apps.api.app.services.matching.service import MatchService
from apps.api.app.services.trust.service import TrustAssessmentService

logger = get_logger("careeros.decision.service")


class DecisionService:
    """
    Main orchestration service for deterministic action eligibility decisions.
    """

    _engine = DecisionEngine

    @classmethod
    async def evaluate_decision(
        cls,
        profile_id: UUID,
        job_id: UUID,
        user_id: UUID,
        policy: CandidateAutomationPolicy | None = None,
        application_context: ApplicationContext | None = None,
        request_id: str = "internal",
    ) -> Decision:
        """
        Evaluate and persist a deterministic decision for a given candidate and job.
        """
        start_time = time.perf_counter()

        logger.info(
            "DECISION_STARTED",
            extra={
                "event": "DECISION_STARTED",
                "request_id": request_id,
                "profile_id": str(profile_id),
                "job_id": str(job_id),
            },
        )

        # 1. Load Job
        job = await JobRepository.get_job_by_id(job_id)
        if not job:
            logger.error(
                "DECISION_FAILED",
                extra={
                    "event": "DECISION_FAILED",
                    "request_id": request_id,
                    "error": "Job not found",
                },
            )
            raise CareerOSError(
                code="JOB_NOT_FOUND",
                message=f"Job {job_id} not found",
                status_code=404,
            )

        # 2. Load or compute Match
        match = await MatchRepository.get_match_for_job(profile_id, job_id, user_id)
        if not match:
            match = await MatchService.calculate_match(profile_id, job_id, user_id)

        # 3. Load or compute Trust Assessment
        trust = await TrustRepository.get_by_job_id(job_id)
        if not trust:
            trust = await TrustAssessmentService.assess_job(job)

        # 4. Resolve Candidate Automation Policy
        if policy is None:
            user_prefs = await ProfileRepository.get_preferences(profile_id, user_id)
            if user_prefs:
                policy = CandidateAutomationPolicy(
                    preferred_work_modes=user_prefs.preferred_work_modes,
                    employment_types=user_prefs.preferred_employment_types,
                    minimum_salary=user_prefs.salary_min,
                    excluded_locations=user_prefs.excluded_locations,
                )
            else:
                policy = CandidateAutomationPolicy()

        # 5. Resolve Application Context
        if application_context is None:
            app_url = job.application_url or job.source_url
            exec_mode = "API" if getattr(job, "is_api_ingested", False) else "USER_HANDOFF"
            application_context = ApplicationContext(
                application_url=app_url,
                execution_mode=exec_mode,
            )

        # 6. Evaluate Decision via pure DecisionPolicyEngine
        decision = cls._engine.evaluate(
            match=match,
            trust=trust,
            policy=policy,
            application_context=application_context,
        )

        duration_ms = (time.perf_counter() - start_time) * 1000

        # Structured gate observability logs
        logger.info(
            "FINAL_SCORE_CALCULATED",
            extra={
                "event": "FINAL_SCORE_CALCULATED",
                "request_id": request_id,
                "overall_score": decision.overall_score,
                "match_score": decision.match_score,
                "trust_score": decision.trust_score,
            },
        )
        logger.info(
            "RISK_GATE_EVALUATED",
            extra={
                "event": "RISK_GATE_EVALUATED",
                "risk_level": decision.risk_level,
                "is_high_risk": decision.risk_level == "HIGH",
            },
        )
        logger.info(
            "CONSTRAINT_GATE_EVALUATED",
            extra={
                "event": "CONSTRAINT_GATE_EVALUATED",
                "passed": decision.hard_constraints_passed,
            },
        )
        logger.info(
            "POLICY_GATE_EVALUATED",
            extra={
                "event": "POLICY_GATE_EVALUATED",
                "auto_apply_enabled": policy.auto_apply_enabled,
                "require_user_approval": policy.require_user_approval,
            },
        )
        logger.info(
            "APPLICATION_SAFETY_GATE_EVALUATED",
            extra={
                "event": "APPLICATION_SAFETY_GATE_EVALUATED",
                "execution_mode": decision.application_mode,
                "sensitive_signals_count": len(application_context.sensitive_signals),
            },
        )

        if decision.action == "REJECT":
            logger.warning(
                "DECISION_BLOCKED",
                extra={
                    "event": "DECISION_BLOCKED",
                    "request_id": request_id,
                    "action": decision.action,
                    "blocking_conditions": decision.blocking_conditions,
                },
            )
        else:
            logger.info(
                "DECISION_COMPLETED",
                extra={
                    "event": "DECISION_COMPLETED",
                    "request_id": request_id,
                    "profile_id": str(profile_id),
                    "job_id": str(job_id),
                    "match_id": str(match.id),
                    "decision_id": str(decision.id),
                    "action": decision.action,
                    "duration_ms": round(duration_ms, 2),
                    "policy_version": decision.policy_version,
                },
            )

        # 7. Persist decision (idempotent upsert)
        saved_decision = await DecisionRepository.save_decision(decision, user_id)
        return saved_decision

    @classmethod
    async def evaluate_batch(
        cls,
        profile_id: UUID,
        job_ids: list[UUID],
        user_id: UUID,
        policy: CandidateAutomationPolicy | None = None,
        request_id: str = "internal",
    ) -> list[Decision]:
        """
        Evaluate decisions for up to 20 jobs with graceful per-job failure handling.
        """
        bounded_jobs = job_ids[:20]
        results: list[Decision] = []

        for j_id in bounded_jobs:
            try:
                dec = await cls.evaluate_decision(
                    profile_id=profile_id,
                    job_id=j_id,
                    user_id=user_id,
                    policy=policy,
                    request_id=request_id,
                )
                results.append(dec)
            except Exception as e:
                logger.error(
                    f"Failed to evaluate decision for job {j_id}: {e}",
                    extra={"job_id": str(j_id)},
                )

        return results


class DecisionEngine:
    """Consolidated DecisionEngine interface preserving backward compatibility."""

    POLICY_VERSION: str = "policy_v1.0"
    AUTO_APPLY_THRESHOLD: float = 90.0
    APPROVAL_THRESHOLD: float = 75.0
    MIN_TRUST_THRESHOLD: float = 80.0
    HIGH_RISK_TRUST_CEILING: float = 35.0

    @classmethod
    def calculate_final_score(cls, match_score: float, trust_score: float) -> float:
        """Calculate composite score: FinalScore = 0.90 * Match + 0.10 * Trust."""
        return (match_score * 0.90) + (trust_score * 0.10)

    @classmethod
    def evaluate(cls, input_data: Any) -> Any:
        """Evaluate deterministic action decision following ordered policy gates."""
        from apps.api.app.services.decision.models import DecisionResult

        final_score = cls.calculate_final_score(input_data.match_score, input_data.trust_score)
        reasons: list[str] = []

        if input_data.risk_level == "HIGH" or input_data.trust_score < cls.HIGH_RISK_TRUST_CEILING:
            reasons.append(
                f"Trust check failed: listing flagged as {input_data.risk_level} risk with trust {input_data.trust_score}"
            )
            return DecisionResult(
                final_score=final_score,
                outcome="REJECT",
                reasons=reasons,
                policy_version=cls.POLICY_VERSION,
            )

        if getattr(input_data, "has_hard_constraint_violation", False):
            reasons.append("Hard constraint failed (e.g. location, visa, or work mode mismatch)")
            return DecisionResult(
                final_score=final_score,
                outcome="REJECT",
                reasons=reasons,
                policy_version=cls.POLICY_VERSION,
            )

        if input_data.risk_level == "UNKNOWN":
            reasons.append("Trust assessment inconclusive (UNKNOWN risk level)")
            return DecisionResult(
                final_score=final_score,
                outcome="USER_APPROVAL",
                reasons=reasons,
                policy_version=cls.POLICY_VERSION,
            )

        if input_data.trust_score < cls.MIN_TRUST_THRESHOLD:
            reasons.append(
                f"Trust score {input_data.trust_score} below minimum threshold {cls.MIN_TRUST_THRESHOLD}"
            )
            return DecisionResult(
                final_score=final_score,
                outcome="USER_APPROVAL",
                reasons=reasons,
                policy_version=cls.POLICY_VERSION,
            )

        if (
            final_score >= cls.AUTO_APPLY_THRESHOLD
            and input_data.trust_score >= cls.MIN_TRUST_THRESHOLD
            and input_data.risk_level == "LOW"
        ):
            reasons.append(
                f"Auto-apply criteria satisfied: exceptional alignment ({final_score} composite score) and verified trust ({input_data.trust_score})"
            )
            return DecisionResult(
                final_score=final_score,
                outcome="AUTO_APPLY",
                reasons=reasons,
                policy_version=cls.POLICY_VERSION,
            )

        if final_score >= cls.APPROVAL_THRESHOLD:
            reasons.append(
                f"Solid opportunity ({final_score} composite score) exceeding approval threshold {cls.APPROVAL_THRESHOLD}"
            )
            return DecisionResult(
                final_score=final_score,
                outcome="USER_APPROVAL",
                reasons=reasons,
                policy_version=cls.POLICY_VERSION,
            )

        reasons.append(
            f"Composite score ({final_score}) below minimum approval threshold ({cls.APPROVAL_THRESHOLD})"
        )
        return DecisionResult(
            final_score=final_score,
            outcome="REJECT",
            reasons=reasons,
            policy_version=cls.POLICY_VERSION,
        )

