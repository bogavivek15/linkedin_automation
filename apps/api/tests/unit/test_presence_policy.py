"""
Unit tests for CareerOS Phase 15 — Presence Safety & Grounding Policies.
"""

import pytest
from apps.api.app.domain.presence.policy import (
    PresencePolicy,
    UngroundedPresenceContentError,
)


def test_presence_policy_requires_evidence_grounding():
    """
    Drafts without evidence citations must be rejected by policy.
    """
    with pytest.raises(UngroundedPresenceContentError):
        PresencePolicy.validate_content_grounding(
            title="Building Large Scale Systems",
            content_body="In my extensive experience building distributed databases...",
            evidence_ids=[],  # Zero grounding evidence
        )


def test_presence_policy_rejects_empty_content():
    """
    Empty or stub content is rejected.
    """
    with pytest.raises(UngroundedPresenceContentError):
        PresencePolicy.validate_content_grounding(
            title="",
            content_body="Short",
            evidence_ids=["ev-1"],
        )


def test_presence_policy_resolves_user_handoff_without_oauth():
    """
    If official OAuth is not connected, publication mode defaults strictly to USER_HANDOFF.
    Never attempts unauthorized browser automation.
    """
    mode = PresencePolicy.resolve_publication_mode(
        requested_mode="OFFICIAL_API",
        has_authorized_oauth=False,
    )
    assert mode == "USER_HANDOFF"


def test_presence_policy_quality_score_calculation():
    """
    Calculates deterministic quality score from length and evidence density.
    """
    score = PresencePolicy.calculate_quality_score(
        content_body="A".join(["word "] * 80),
        evidence_count=2,
    )
    assert 70.0 <= score <= 100.0
