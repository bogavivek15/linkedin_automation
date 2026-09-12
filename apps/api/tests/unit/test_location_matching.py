"""
CareerOS Phase 8 — Location Matching Tests.
"""

from apps.api.app.domain.matching.location_matcher import match_location
from apps.api.app.domain.matching.models import LocationMatchResult


def test_remote_job_remote_preference():
    """Remote job + candidate prefers remote → MATCH, 100."""
    score, result = match_location(
        job_location="Worldwide",
        job_work_mode="REMOTE",
        candidate_location="San Francisco",
        candidate_preferred_locations=["San Francisco"],
        candidate_preferred_work_modes=["REMOTE", "HYBRID"],
    )
    assert result == LocationMatchResult.MATCH
    assert score == 100.0


def test_remote_job_no_mode_preference():
    """Remote job, no work mode preference → PARTIAL_MATCH."""
    score, result = match_location(
        job_location="Worldwide",
        job_work_mode="REMOTE",
        candidate_location="NYC",
        candidate_preferred_locations=[],
        candidate_preferred_work_modes=[],
    )
    assert result == LocationMatchResult.PARTIAL_MATCH
    assert score >= 70.0


def test_hybrid_job_location_match():
    """Hybrid job with location overlap + mode preference → MATCH."""
    score, result = match_location(
        job_location="San Francisco",
        job_work_mode="HYBRID",
        candidate_location="San Francisco",
        candidate_preferred_locations=["San Francisco"],
        candidate_preferred_work_modes=["HYBRID"],
    )
    assert result == LocationMatchResult.MATCH
    assert score == 100.0


def test_hybrid_job_no_location_overlap():
    """Hybrid job, no location overlap → MISMATCH."""
    score, result = match_location(
        job_location="London",
        job_work_mode="HYBRID",
        candidate_location="Tokyo",
        candidate_preferred_locations=["Tokyo"],
        candidate_preferred_work_modes=["ONSITE"],
    )
    assert result == LocationMatchResult.MISMATCH


def test_onsite_job_location_match():
    """Onsite job with location match → MATCH or PARTIAL_MATCH."""
    score, result = match_location(
        job_location="San Francisco",
        job_work_mode="ONSITE",
        candidate_location="San Francisco",
        candidate_preferred_locations=["San Francisco"],
        candidate_preferred_work_modes=["ONSITE"],
    )
    assert result == LocationMatchResult.MATCH
    assert score == 100.0


def test_onsite_job_location_mismatch():
    """Onsite job, wrong location → MISMATCH."""
    score, result = match_location(
        job_location="London",
        job_work_mode="ONSITE",
        candidate_location="Tokyo",
        candidate_preferred_locations=["Tokyo"],
        candidate_preferred_work_modes=["REMOTE"],
    )
    assert result == LocationMatchResult.MISMATCH
    assert score <= 20.0


def test_unknown_work_mode_unknown_location():
    """All unknown → UNKNOWN, 50."""
    score, result = match_location(
        job_location=None,
        job_work_mode="UNKNOWN",
        candidate_location=None,
        candidate_preferred_locations=[],
        candidate_preferred_work_modes=[],
    )
    assert result == LocationMatchResult.UNKNOWN
    assert score == 50.0


def test_candidate_prefers_remote_job_is_hybrid():
    """Candidate prefers REMOTE, job is HYBRID → PARTIAL_MATCH."""
    score, result = match_location(
        job_location="San Francisco",
        job_work_mode="HYBRID",
        candidate_location="Denver",
        candidate_preferred_locations=["Denver"],
        candidate_preferred_work_modes=["REMOTE"],
    )
    assert result == LocationMatchResult.PARTIAL_MATCH


def test_partial_location_substring():
    """Location substring match (e.g., 'SF' in 'San Francisco')."""
    score, result = match_location(
        job_location="San Francisco, CA",
        job_work_mode="ONSITE",
        candidate_location=None,
        candidate_preferred_locations=["San Francisco"],
        candidate_preferred_work_modes=["ONSITE"],
    )
    assert result == LocationMatchResult.MATCH
    assert score == 100.0
