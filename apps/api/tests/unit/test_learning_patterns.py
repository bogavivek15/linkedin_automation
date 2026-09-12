"""
Unit tests for CareerOS Phase 13 — Learning Pattern Detection & Insights.
"""

import pytest
from apps.api.app.domain.learning.insights import (
    CareerInsightGenerator,
    ImmutableCandidateFactViolationError,
)
from apps.api.app.domain.learning.models import CareerOutcome
from apps.api.app.domain.learning.patterns import OutcomePatternDetector


def test_pattern_detection_high_match_conversion():
    user_id = "00000000-0000-0000-0000-000000000001"
    profile_id = "prof-1"

    outcomes = [
        CareerOutcome(
            user_id=user_id,
            profile_id=profile_id,
            job_id=f"00000000-0000-0000-0000-00000000001{i}",
            outcome_type="INTERVIEW_SCHEDULED" if i % 2 == 0 else "REJECTED_SCREEN",
            notes="backend Python API distributed systems role",
            match_score=90.0,
            trust_score=90.0,
        )
        for i in range(6)
    ]

    patterns = OutcomePatternDetector.detect_patterns(
        user_id=user_id,
        profile_id=profile_id,
        outcomes=outcomes,
    )

    assert len(patterns) >= 1
    boost = next((p for p in patterns if p.pattern_type == "INTERVIEW_CONVERSION_BOOST"), None)
    assert boost is not None
    assert boost.evidence_sample_count == 6
    assert boost.confidence >= 0.8


def test_insight_generator_creates_evidence_backed_recommendations():
    user_id = "00000000-0000-0000-0000-000000000001"
    profile_id = "prof-1"

    outcomes = [
        CareerOutcome(
            user_id=user_id,
            profile_id=profile_id,
            job_id=f"00000000-0000-0000-0000-00000000002{i}",
            outcome_type="REJECTED_SCREEN",
            extracted_skill_gaps=["Kubernetes", "AWS"] if i < 4 else ["Kubernetes"],
        )
        for i in range(5)
    ]

    patterns = OutcomePatternDetector.detect_patterns(
        user_id=user_id,
        profile_id=profile_id,
        outcomes=outcomes,
    )
    insights = CareerInsightGenerator.generate_insights(
        user_id=user_id,
        profile_id=profile_id,
        patterns=patterns,
    )

    assert len(insights) >= 1
    skill_insight = next((ins for ins in insights if ins.category == "SKILL_GAP"), None)
    assert skill_insight is not None
    assert "Kubernetes" in skill_insight.title
    assert skill_insight.severity == "RECOMMENDATION"


def test_immutable_candidate_fact_invariant_enforcement():
    """
    Ensures that learning models or updates cannot mutate immutable candidate facts.
    """
    with pytest.raises(ImmutableCandidateFactViolationError):
        CareerInsightGenerator.assert_fact_immutability(
            original_skills={"Python", "FastAPI", "Postgres"},
            proposed_skills={"Python", "FastAPI", "Postgres", "FabricatedDegreeSkill"},
        )
