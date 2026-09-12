"""
Unit tests for CareerOS Phase 12 Lifecycle Transition Policy.
"""

import pytest
from apps.api.app.domain.application_lifecycle.policy import (
    InvalidLifecycleTransitionError,
    LifecyclePolicy,
)


def test_valid_transitions_pass():
    # DISCOVERED -> PREPARED
    LifecyclePolicy.validate_transition("DISCOVERED", "PREPARED", "MANUALLY_ENTERED")
    # PREPARED -> APPROVED
    LifecyclePolicy.validate_transition("PREPARED", "APPROVED", "USER_CONFIRMATION")
    # APPROVED -> SUBMITTED
    LifecyclePolicy.validate_transition("APPROVED", "SUBMITTED", "USER_CONFIRMATION")
    # SUBMITTED -> ACKNOWLEDGED
    LifecyclePolicy.validate_transition("SUBMITTED", "ACKNOWLEDGED", "RECRUITER_COMMUNICATION")
    # ACKNOWLEDGED -> INTERVIEW
    LifecyclePolicy.validate_transition("ACKNOWLEDGED", "INTERVIEW", "RECRUITER_COMMUNICATION")
    # INTERVIEW -> OFFER
    LifecyclePolicy.validate_transition("INTERVIEW", "OFFER", "RECRUITER_COMMUNICATION")


def test_submitted_to_interview_direct_jump_is_prohibited():
    # Invariant: Never automatically infer SUBMITTED -> INTERVIEW without proper progression
    with pytest.raises(InvalidLifecycleTransitionError) as exc:
        LifecyclePolicy.validate_transition("SUBMITTED", "INTERVIEW", "USER_CONFIRMATION")
    assert "Direct transition from SUBMITTED to INTERVIEW is prohibited" in str(exc.value)


def test_illegal_transition_raises_error():
    with pytest.raises(InvalidLifecycleTransitionError) as exc:
        LifecyclePolicy.validate_transition("REJECTED", "INTERVIEW", "USER_CONFIRMATION")
    assert "not permitted by lifecycle graph" in str(exc.value)


def test_strict_transitions_require_valid_evidence():
    with pytest.raises(InvalidLifecycleTransitionError) as exc:
        LifecyclePolicy.validate_transition("INTERVIEW", "OFFER", "MANUALLY_ENTERED")
    assert "insufficient to prove progression" in str(exc.value)
