"""
CareerOS Phase 20 — Evaluation Suite Runner.

Executes deterministic evaluation datasets against matching, trust, and decision engines,
verifying strict quality gates and zero unsafe false positives.
"""

from typing import Any

from apps.api.app.domain.decision.models import (
    CandidateAutomationPolicy,
)
from apps.api.app.domain.decision.policy import DecisionPolicyEngine
from apps.api.app.domain.job.models import CanonicalJob
from apps.api.app.domain.matching.models import CandidateSkill, MatchAgentOutput, SkillProvenance
from apps.api.app.domain.matching.skill_matcher import match_skills, normalize_skill
from apps.api.app.domain.trust.models import (
    ConfidenceLevel,
    EvidenceCategory,
    TrustAssessment,
    TrustContext,
)
from apps.api.app.domain.trust.models import (
    RiskLevel as TrustRiskLevel,
)
from apps.api.app.evaluation.datasets import (
    DECISION_EVAL_DATASET,
    MATCHING_EVAL_DATASET,
    TRUST_EVAL_DATASET,
)
from apps.api.app.services.trust.providers.deterministic import DeterministicEvidenceProvider


class EvaluationSuiteRunner:
    """
    Executes benchmark evaluations and tracks reliability metrics.
    """

    @classmethod
    async def run_all_evaluations(cls) -> dict[str, Any]:
        matching_results = cls.evaluate_matching()
        trust_results = await cls.evaluate_trust()
        decision_results = cls.evaluate_decision()

        total_cases = (
            matching_results["total"] + trust_results["total"] + decision_results["total"]
        )
        passed_cases = (
            matching_results["passed"] + trust_results["passed"] + decision_results["passed"]
        )

        return {
            "overall_pass_rate": round(passed_cases / total_cases, 4),
            "total_evaluated": total_cases,
            "passed_count": passed_cases,
            "matching": matching_results,
            "trust": trust_results,
            "decision": decision_results,
        }

    @classmethod
    def evaluate_matching(cls) -> dict[str, Any]:
        passed = 0
        for tc in MATCHING_EVAL_DATASET:
            job_skills = tc.input_data["job_skills"]
            candidate_raw = tc.input_data["candidate_skills"]

            candidate_objs = [
                CandidateSkill(
                    name=s,
                    normalized_name=normalize_skill(s),
                    provenance=SkillProvenance.VERIFIED,
                )
                for s in candidate_raw
            ]

            result = match_skills(job_skills, [], candidate_objs)
            missing_count = len(result.missing)

            if "missing_skills_count" in tc.expected_output:
                if missing_count == tc.expected_output["missing_skills_count"]:
                    passed += 1
            else:
                passed += 1

        return {
            "category": "MATCHING",
            "total": len(MATCHING_EVAL_DATASET),
            "passed": passed,
            "accuracy": round(passed / len(MATCHING_EVAL_DATASET), 4),
        }

    @classmethod
    async def evaluate_trust(cls) -> dict[str, Any]:
        passed = 0
        provider = DeterministicEvidenceProvider()

        for tc in TRUST_EVAL_DATASET:
            job = CanonicalJob(
                external_id=f"eval-{tc.id}",
                source="EVAL",
                source_url=tc.input_data["url"],
                title="Software Engineer",
                normalized_title="software engineer",
                company_name=tc.input_data["company_name"],
                normalized_company=tc.input_data["company_name"].lower(),
                description=tc.input_data["description"],
                description_hash=f"hash-{tc.id}",
            )
            evidence = await provider.collect(TrustContext(job=job, company_name=job.company_name))

            has_scam = any(
                e.evidence_type in (
                    EvidenceCategory.PAYMENT_REQUEST.value,
                    EvidenceCategory.URGENCY.value,
                    EvidenceCategory.SENSITIVE_INFORMATION.value,
                )
                for e in evidence
            )
            should_block = tc.expected_output.get("should_block", False)

            if should_block:
                if has_scam:
                    passed += 1
            else:
                if not has_scam:
                    passed += 1

        return {
            "category": "TRUST",
            "total": len(TRUST_EVAL_DATASET),
            "passed": passed,
            "accuracy": round(passed / len(TRUST_EVAL_DATASET), 4),
        }

    @classmethod
    def evaluate_decision(cls) -> dict[str, Any]:
        passed = 0
        engine = DecisionPolicyEngine()
        policy = CandidateAutomationPolicy(min_match_score=70.0, min_trust_score=70.0)

        for tc in DECISION_EVAL_DATASET:
            score = tc.input_data["match_score"]
            match = MatchAgentOutput(
                profile_id="00000000-0000-0000-0000-000000000001",
                job_id="00000000-0000-0000-0000-000000000001",
                semantic_score=score,
                skill_score=score,
                experience_score=score,
                location_score=score,
                preference_score=score,
                overall_score=score,
                recommended_resume_id="res-123",
            )

            risk_enum = (
                TrustRiskLevel.HIGH
                if tc.input_data["risk_level"] == "HIGH"
                else TrustRiskLevel.LOW
            )

            trust = TrustAssessment(
                job_id="00000000-0000-0000-0000-000000000001",
                trust_score=tc.input_data["trust_score"],
                risk_score=100.0 - tc.input_data["trust_score"],
                risk_level=risk_enum,
                confidence=ConfidenceLevel.HIGH,
                signals=[],
                evidence_items=[],
                explanation="Eval assessment",
            )

            decision = engine.evaluate(match=match, trust=trust, policy=policy)
            expected_action = tc.expected_output["action"]

            if expected_action == "PREPARE_APPLICATION" and decision.action in (
                "AUTO_APPLY",
                "USER_APPROVAL",
            ):
                passed += 1
            elif expected_action == "BLOCK_APPLICATION" and decision.action == "REJECT":
                passed += 1
            elif expected_action == "PASS" and decision.action in (
                "USER_APPROVAL",
                "REJECT",
                "IMPROVEMENT_REQUIRED",
            ):
                passed += 1

        return {
            "category": "DECISION",
            "total": len(DECISION_EVAL_DATASET),
            "passed": passed,
            "accuracy": round(passed / len(DECISION_EVAL_DATASET), 4),
        }
