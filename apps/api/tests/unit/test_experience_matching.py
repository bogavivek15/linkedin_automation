"""
CareerOS Phase 8 — Experience Matching Tests.
"""

from apps.api.app.domain.matching.experience_matcher import match_experience


def test_strong_match_exceeds():
    """Candidate exceeds job requirement → STRONG_MATCH, 100."""
    score, label = match_experience(3.0, 5.0)
    assert score == 100.0
    assert label == "STRONG_MATCH"


def test_strong_match_exact():
    """Candidate exactly meets requirement → STRONG_MATCH, 100."""
    score, label = match_experience(5.0, 5.0)
    assert score == 100.0
    assert label == "STRONG_MATCH"


def test_entry_level_no_requirement():
    """No job experience requirement → ENTRY_LEVEL, 100."""
    score, label = match_experience(None, 2.0)
    assert score == 100.0
    assert label == "ENTRY_LEVEL"


def test_entry_level_zero_requirement():
    """Job requires 0 years → ENTRY_LEVEL, 100."""
    score, label = match_experience(0, 2.0)
    assert score == 100.0
    assert label == "ENTRY_LEVEL"


def test_unknown_experience():
    """Candidate experience is unknown → UNKNOWN, 40."""
    score, label = match_experience(3.0, None)
    assert score == 40.0
    assert label == "UNKNOWN"


def test_partial_match_75_percent():
    """Candidate has 75% of required experience → PARTIAL_MATCH."""
    score, label = match_experience(4.0, 3.0)  # 3/4 = 75%
    assert label == "PARTIAL_MATCH"
    assert score >= 70.0


def test_partial_match_50_percent():
    """Candidate has 50% of required experience → PARTIAL_MATCH."""
    score, label = match_experience(4.0, 2.0)  # 2/4 = 50%
    assert label == "PARTIAL_MATCH"
    assert 40.0 <= score <= 70.0


def test_mismatch_low_experience():
    """Candidate has very little experience vs requirement → MISMATCH."""
    score, label = match_experience(10.0, 1.0)  # 1/10 = 10%
    assert label == "MISMATCH"
    assert score < 40.0


def test_mismatch_zero_experience():
    """Candidate has zero experience → MISMATCH, 10."""
    score, label = match_experience(5.0, 0.0)
    assert score == 10.0
    assert label == "MISMATCH"


def test_both_none():
    """Both None → ENTRY_LEVEL (no requirement)."""
    score, label = match_experience(None, None)
    assert score == 100.0
    assert label == "ENTRY_LEVEL"
