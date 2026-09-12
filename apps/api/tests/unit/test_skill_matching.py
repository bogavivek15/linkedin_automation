"""
CareerOS Phase 8 — Skill Matching Tests.

Covers normalization, aliases, MATCHED/MISSING/UNCERTAIN classification, scoring formula.
"""

from apps.api.app.domain.matching.models import CandidateSkill, SkillProvenance
from apps.api.app.domain.matching.skill_matcher import (
    SkillMatchStatus,
    match_skills,
    normalize_skill,
)

# ---------------------------------------------------------------------------
# Normalization Tests
# ---------------------------------------------------------------------------


def test_normalize_basic():
    assert normalize_skill("Python") == "python"


def test_normalize_whitespace():
    assert normalize_skill("  Python  ") == "python"


def test_normalize_alias_postgres():
    assert normalize_skill("PostgreSQL") == "postgresql"
    assert normalize_skill("postgres") == "postgresql"
    assert normalize_skill("pg") == "postgresql"


def test_normalize_alias_javascript():
    assert normalize_skill("JavaScript") == "javascript"
    assert normalize_skill("JS") == "javascript"
    assert normalize_skill("js") == "javascript"


def test_normalize_alias_typescript():
    assert normalize_skill("TypeScript") == "typescript"
    assert normalize_skill("TS") == "typescript"


def test_normalize_alias_ml():
    assert normalize_skill("Machine Learning") == "machine-learning"
    assert normalize_skill("ML") == "machine-learning"


def test_normalize_alias_ai():
    assert normalize_skill("Artificial Intelligence") == "artificial-intelligence"
    assert normalize_skill("AI") == "artificial-intelligence"


def test_normalize_alias_kubernetes():
    assert normalize_skill("Kubernetes") == "kubernetes"
    assert normalize_skill("K8s") == "kubernetes"


def test_normalize_alias_docker():
    assert normalize_skill("Docker") == "docker"


def test_normalize_alias_fastapi():
    assert normalize_skill("FastAPI") == "fastapi"
    assert normalize_skill("fast api") == "fastapi"


def test_normalize_empty():
    assert normalize_skill("") == ""


def test_normalize_trailing_punctuation():
    assert normalize_skill("Python,") == "python"


# ---------------------------------------------------------------------------
# Skill Matching Classification Tests
# ---------------------------------------------------------------------------


def _make_candidate_skills(skills_dict: dict[str, str]) -> list[CandidateSkill]:
    """Helper: create CandidateSkill list from {name: provenance_str}."""
    result = []
    for name, prov in skills_dict.items():
        result.append(
            CandidateSkill(
                name=name,
                normalized_name=normalize_skill(name),
                provenance=SkillProvenance(prov),
            )
        )
    return result


def test_exact_match_verified():
    """Verified skills should be MATCHED."""
    candidate = _make_candidate_skills({"Python": "VERIFIED", "FastAPI": "VERIFIED"})
    result = match_skills(["Python", "FastAPI"], [], candidate)
    assert sorted(result.matched) == ["FastAPI", "Python"]
    assert result.missing == []
    assert result.uncertain == []
    assert result.score == 100.0


def test_missing_skill():
    """Skills not in candidate profile should be MISSING."""
    candidate = _make_candidate_skills({"Python": "VERIFIED"})
    result = match_skills(["Python", "Docker"], [], candidate)
    assert "Python" in result.matched
    assert "Docker" in result.missing
    assert result.score == 50.0  # 1/2 required matched


def test_uncertain_skill_inferred():
    """INFERRED provenance → UNCERTAIN status."""
    candidate = _make_candidate_skills({"Kubernetes": "INFERRED"})
    result = match_skills(["Kubernetes"], [], candidate)
    assert result.matched == []
    assert result.uncertain == ["Kubernetes"]
    assert result.score == 0.0  # UNCERTAIN doesn't count as matched


def test_uncertain_skill_unknown():
    """UNKNOWN provenance → UNCERTAIN status."""
    candidate = _make_candidate_skills({"AWS": "UNKNOWN"})
    result = match_skills(["AWS"], [], candidate)
    assert result.uncertain == ["AWS"]
    assert result.score == 0.0


def test_alias_matching():
    """Candidate has 'postgres', job requires 'PostgreSQL' → should match via alias."""
    candidate = _make_candidate_skills({"postgres": "VERIFIED"})
    result = match_skills(["PostgreSQL"], [], candidate)
    assert "PostgreSQL" in result.matched
    assert result.score == 100.0


def test_required_vs_preferred_weighting():
    """Required skills carry 75% weight, preferred 25%."""
    candidate = _make_candidate_skills({
        "Python": "VERIFIED",
        "FastAPI": "VERIFIED",
    })
    # 2/2 required matched, 0/2 preferred matched
    result = match_skills(
        ["Python", "FastAPI"],
        ["Docker", "Kubernetes"],
        candidate,
    )
    # score = 0.75 * (2/2) + 0.25 * (0/2) = 0.75 * 100 = 75.0
    assert result.score == 75.0


def test_required_and_preferred_all_matched():
    """All required and preferred matched → score = 100."""
    candidate = _make_candidate_skills({
        "Python": "VERIFIED",
        "FastAPI": "VERIFIED",
        "Docker": "VERIFIED",
        "Redis": "VERIFIED",
    })
    result = match_skills(
        ["Python", "FastAPI"],
        ["Docker", "Redis"],
        candidate,
    )
    assert result.score == 100.0


def test_zero_required_skills():
    """No required skills — only preferred."""
    candidate = _make_candidate_skills({"Docker": "VERIFIED"})
    result = match_skills([], ["Docker", "Redis"], candidate)
    # Only preferred: 1/2 = 50%
    assert result.score == 50.0


def test_zero_preferred_skills():
    """No preferred skills — required carries 100%."""
    candidate = _make_candidate_skills({"Python": "VERIFIED"})
    result = match_skills(["Python", "FastAPI"], [], candidate)
    # 1/2 required = 50%
    assert result.score == 50.0


def test_zero_required_zero_preferred():
    """No skills specified → neutral 50."""
    candidate = _make_candidate_skills({"Python": "VERIFIED"})
    result = match_skills([], [], candidate)
    assert result.score == 50.0


def test_all_missing():
    """All required missing → 0."""
    candidate = _make_candidate_skills({})
    result = match_skills(["Python", "FastAPI"], [], candidate)
    assert result.score == 0.0
    assert sorted(result.missing) == ["FastAPI", "Python"]


def test_student_confirmed_counts_as_matched():
    """STUDENT_CONFIRMED provenance → MATCHED."""
    candidate = _make_candidate_skills({"Docker": "STUDENT_CONFIRMED"})
    result = match_skills(["Docker"], [], candidate)
    assert "Docker" in result.matched
    assert result.score == 100.0


def test_skill_details_contain_all_skills():
    """Every job skill should have a corresponding detail entry."""
    candidate = _make_candidate_skills({"Python": "VERIFIED"})
    result = match_skills(["Python", "FastAPI"], ["Docker"], candidate)
    assert len(result.details) == 3
    job_skills_in_details = {d.job_skill for d in result.details}
    assert job_skills_in_details == {"Python", "FastAPI", "Docker"}


def test_details_is_required_flag():
    """Required skills have is_required=True, preferred have is_required=False."""
    candidate = _make_candidate_skills({"Python": "VERIFIED"})
    result = match_skills(["Python"], ["Docker"], candidate)
    for d in result.details:
        if d.job_skill == "Python":
            assert d.is_required is True
        elif d.job_skill == "Docker":
            assert d.is_required is False


def test_case_insensitive_matching():
    """Skills should match case-insensitively."""
    candidate = _make_candidate_skills({"python": "VERIFIED"})
    result = match_skills(["Python"], [], candidate)
    assert "Python" in result.matched


def test_semantic_similarity_does_not_prove_skill():
    """
    Core invariant: if candidate has Python VERIFIED but not Kubernetes,
    Kubernetes must NOT be marked as matched just because Python and Kubernetes
    are semantically related.
    """
    candidate = _make_candidate_skills({"Python": "VERIFIED"})
    result = match_skills(["Python", "Kubernetes"], [], candidate)
    assert "Python" in result.matched
    assert "Kubernetes" in result.missing
    # Kubernetes is NOT inferred from Python
    kubernetes_detail = next(d for d in result.details if d.job_skill == "Kubernetes")
    assert kubernetes_detail.status == SkillMatchStatus.MISSING
