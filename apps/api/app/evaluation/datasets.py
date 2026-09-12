"""
CareerOS Phase 20 — Deterministic Evaluation Datasets.

Ground-truth benchmark test cases across:
1. Matching Engine
2. Trust & Safety Policy
3. Application Claim Grounding
4. Deterministic Decision Engine
"""

from typing import Any

from pydantic import BaseModel


class EvalTestCase(BaseModel):
    id: str
    category: str
    input_data: dict[str, Any]
    expected_output: dict[str, Any]


# 1. Matching Evaluation Dataset
MATCHING_EVAL_DATASET = [
    EvalTestCase(
        id="match-strong-python",
        category="MATCHING",
        input_data={
            "job_skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
            "candidate_skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Git"],
        },
        expected_output={"min_score": 85.0, "missing_skills_count": 0},
    ),
    EvalTestCase(
        id="match-missing-essential-skill",
        category="MATCHING",
        input_data={
            "job_skills": ["Kubernetes", "Golang", "C++"],
            "candidate_skills": ["Python", "FastAPI"],
        },
        expected_output={"max_score": 40.0, "missing_skills_count": 3},
    ),
]

# 2. Trust Evaluation Dataset
TRUST_EVAL_DATASET = [
    EvalTestCase(
        id="trust-legitimate-enterprise",
        category="TRUST",
        input_data={
            "company_name": "Google",
            "url": "https://careers.google.com/jobs/results/12345",
            "description": "Software engineer role working on distributed storage systems.",
        },
        expected_output={"min_trust_score": 80.0, "expected_risk": "LOW"},
    ),
    EvalTestCase(
        id="trust-payment-scam",
        category="TRUST",
        input_data={
            "company_name": "Global Tech Staffing",
            "url": "http://free-jobs-today.biz/apply",
            "description": "Urgent hire! Remote data entry. Candidate must pay $150 processing fee via wire transfer to begin onboarding.",
        },
        expected_output={"max_trust_score": 30.0, "expected_risk": "HIGH", "should_block": True},
    ),
    EvalTestCase(
        id="trust-brand-impersonation",
        category="TRUST",
        input_data={
            "company_name": "Apple Inc",
            "url": "http://apple-careers-recruiter-portal.top/job",
            "description": "Hurry up! Direct interview on telegram required to claim your spot.",
        },
        expected_output={"expected_risk": "HIGH", "should_block": True},
    ),
]

# 3. Decision Engine Evaluation Dataset
DECISION_EVAL_DATASET = [
    EvalTestCase(
        id="decision-safe-and-matched",
        category="DECISION",
        input_data={"match_score": 92.0, "trust_score": 88.0, "risk_level": "LOW"},
        expected_output={"action": "PREPARE_APPLICATION"},
    ),
    EvalTestCase(
        id="decision-high-match-suspicious-trust-blocked",
        category="DECISION",
        input_data={"match_score": 98.0, "trust_score": 25.0, "risk_level": "HIGH"},
        expected_output={"action": "BLOCK_APPLICATION"},
    ),
    EvalTestCase(
        id="decision-low-match-skip",
        category="DECISION",
        input_data={"match_score": 42.0, "trust_score": 90.0, "risk_level": "LOW"},
        expected_output={"action": "PASS"},
    ),
]
