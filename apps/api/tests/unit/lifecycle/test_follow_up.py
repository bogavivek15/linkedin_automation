"""
Unit tests for CareerOS Phase 12 Follow-up Communication Intelligence.
"""

from datetime import datetime, timedelta, timezone

from apps.api.app.domain.application_lifecycle.follow_up import FollowUpIntelligenceEngine
from apps.api.app.domain.application_lifecycle.models import LifecycleRecord


def test_follow_up_generated_after_waiting_period():
    six_days_ago = datetime.now(timezone.utc) - timedelta(days=6)
    record = LifecycleRecord(
        id="lic-1",
        application_id="app-1",
        user_id="user-1",
        job_id="job-1",
        current_status="SUBMITTED",
        last_transition_at=six_days_ago,
    )

    job_info = {"title": "Full Stack Developer", "company_name": "Acme Corp"}
    rec = FollowUpIntelligenceEngine.evaluate_follow_up(record, job_info, candidate_name="Maya")

    assert rec is not None
    assert rec.trigger_type == "WAITING_PERIOD_ELAPSED"
    assert rec.status == "PENDING"
    assert "Acme Corp" in rec.template_body
    assert "Full Stack Developer" in rec.template_subject
    assert "Maya" in rec.template_body


def test_no_follow_up_if_waiting_period_not_elapsed():
    two_days_ago = datetime.now(timezone.utc) - timedelta(days=2)
    record = LifecycleRecord(
        id="lic-2",
        application_id="app-2",
        user_id="user-1",
        job_id="job-1",
        current_status="SUBMITTED",
        last_transition_at=two_days_ago,
    )

    rec = FollowUpIntelligenceEngine.evaluate_follow_up(record, {"company_name": "Acme"})
    assert rec is None


def test_interview_thank_you_generated():
    twelve_hours_ago = datetime.now(timezone.utc) - timedelta(hours=12)
    record = LifecycleRecord(
        id="lic-3",
        application_id="app-3",
        user_id="user-1",
        job_id="job-1",
        current_status="INTERVIEW",
        last_transition_at=twelve_hours_ago,
    )

    job_info = {"title": "AI Engineer", "company_name": "OpenTech"}
    rec = FollowUpIntelligenceEngine.evaluate_follow_up(record, job_info)

    assert rec is not None
    assert rec.trigger_type == "POST_INTERVIEW_THANK_YOU"
    assert rec.status == "PENDING"
    assert "Thank you" in rec.template_subject
