"""
Unit tests for CareerOS Phase 11 Execution State Machine.
"""

import pytest
from apps.api.app.domain.execution.state_machine import (
    InvalidExecutionStateTransitionError,
    can_transition,
    transition_state,
)


def test_legal_linear_state_transitions():
    assert can_transition("PREPARED", "READY_FOR_REVIEW")
    assert can_transition("READY_FOR_REVIEW", "APPROVED")
    assert can_transition("APPROVED", "EXECUTION_CHECK")
    assert can_transition("EXECUTION_CHECK", "USER_HANDOFF")
    assert can_transition("EXECUTION_CHECK", "API_EXECUTION")
    assert can_transition("API_EXECUTION", "EXECUTING")
    assert can_transition("EXECUTING", "SUBMITTED")
    assert can_transition("SUBMITTED", "VERIFIED")


def test_legal_user_handoff_transitions():
    assert can_transition("USER_HANDOFF", "SUBMITTED")
    assert can_transition("USER_HANDOFF", "CANCELLED")
    assert can_transition("USER_HANDOFF", "EXPIRED")


def test_illegal_state_jumps_raise_error():
    # Direct jump from PREPARED to SUBMITTED is illegal
    with pytest.raises(InvalidExecutionStateTransitionError):
        transition_state("PREPARED", "SUBMITTED")

    # Direct jump from READY_FOR_REVIEW to VERIFIED is illegal
    with pytest.raises(InvalidExecutionStateTransitionError):
        transition_state("READY_FOR_REVIEW", "VERIFIED")

    # Terminal state transitions are illegal
    with pytest.raises(InvalidExecutionStateTransitionError):
        transition_state("VERIFIED", "SUBMITTED")

    with pytest.raises(InvalidExecutionStateTransitionError):
        transition_state("BLOCKED", "USER_HANDOFF")
