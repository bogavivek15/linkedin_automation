"""
CareerOS Phase 12 — Follow-up Communication Intelligence.

Calculates grounded follow-up recommendations based on waiting periods and lifecycle stages.
Core Invariant:
Never automatically send messages. Generates draft recommendations requiring candidate approval.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from apps.api.app.domain.application_lifecycle.models import (
    FollowUpRecommendation,
    LifecycleRecord,
)

DEFAULT_SUBMISSION_FOLLOW_UP_DAYS = 5
DEFAULT_INTERVIEW_THANK_YOU_HOURS = 24


class FollowUpIntelligenceEngine:
    """
    Evaluates application stage duration and generates human-in-the-loop follow-up drafts.
    """

    @classmethod
    def evaluate_follow_up(
        cls,
        lifecycle: LifecycleRecord,
        job_info: dict[str, Any] | None = None,
        candidate_name: str = "Candidate",
    ) -> FollowUpRecommendation | None:
        """
        Determine if a follow-up message is recommended and generate draft.
        """
        now = datetime.now(timezone.utc)
        job = job_info or {}
        role = job.get("title", "the role")
        company = job.get("company_name", "the hiring team")
        days_since_transition = (now - lifecycle.last_transition_at).total_seconds() / 86400.0

        # Case 1: Post-Submission Waiting Period Elapsed (5+ days)
        if lifecycle.current_status in ("SUBMITTED", "ACKNOWLEDGED"):
            # Check if there is already a pending follow-up
            existing_pending = any(
                f.status == "PENDING" and f.trigger_type == "WAITING_PERIOD_ELAPSED"
                for f in lifecycle.follow_up_recommendations
            )
            if existing_pending:
                return None

            if days_since_transition >= DEFAULT_SUBMISSION_FOLLOW_UP_DAYS:
                subject = f"Following up on application for {role} at {company}"
                body = (
                    f"Dear {company} Hiring Team,\n\n"
                    f"I hope this message finds you well. I recently submitted my application for the {role} "
                    f"position and wanted to reiterate my strong enthusiasm for joining {company}.\n\n"
                    f"Given my background and verified skills relevant to this position, I am confident I can contribute "
                    f"meaningfully to your team's objectives. Please let me know if any additional information or work "
                    f"samples would be helpful as you review candidate profiles.\n\n"
                    f"Thank you for your time and consideration,\n"
                    f"{candidate_name}"
                )

                return FollowUpRecommendation(
                    id=str(uuid4()),
                    lifecycle_id=lifecycle.id,
                    user_id=lifecycle.user_id,
                    trigger_type="WAITING_PERIOD_ELAPSED",
                    status="PENDING",
                    recommended_send_date=now,
                    template_subject=subject,
                    template_body=body,
                )

        # Case 2: Post-Interview Thank You (within 24-48h)
        elif lifecycle.current_status == "INTERVIEW":
            existing_pending = any(
                f.status == "PENDING" and f.trigger_type == "POST_INTERVIEW_THANK_YOU"
                for f in lifecycle.follow_up_recommendations
            )
            if existing_pending:
                return None

            subject = f"Thank you for the opportunity to interview for {role} at {company}"
            body = (
                f"Dear {company} Interview Team,\n\n"
                f"Thank you for taking the time to speak with me regarding the {role} opening. "
                f"I really enjoyed our discussion and learning more about {company}'s current challenges and initiatives.\n\n"
                f"Our conversation further reinforced my excitement about the position and how my experience aligns "
                f"with your team's priorities. Please let me know if you need any additional details from my end as "
                f"you proceed with the selection process.\n\n"
                f"Best regards,\n"
                f"{candidate_name}"
            )

            return FollowUpRecommendation(
                id=str(uuid4()),
                lifecycle_id=lifecycle.id,
                user_id=lifecycle.user_id,
                trigger_type="POST_INTERVIEW_THANK_YOU",
                status="PENDING",
                recommended_send_date=now,
                template_subject=subject,
                template_body=body,
            )

        # Case 3: Assessment Received (preparation & timeline alert)
        elif lifecycle.current_status == "ASSESSMENT":
            existing_pending = any(
                f.status == "PENDING" and f.trigger_type == "ASSESSMENT_PREPARATION_ALERT"
                for f in lifecycle.follow_up_recommendations
            )
            if existing_pending:
                return None

            return FollowUpRecommendation(
                id=str(uuid4()),
                lifecycle_id=lifecycle.id,
                user_id=lifecycle.user_id,
                trigger_type="ASSESSMENT_PREPARATION_ALERT",
                status="PENDING",
                recommended_send_date=now,
                template_subject=f"Assessment Action Plan: {role} at {company}",
                template_body=(
                    f"CareerOS recommends completing the assessment for {role} at {company} within 48-72 hours. "
                    f"Review verified skills in Python, FastAPI, and algorithm fundamentals before starting."
                ),
            )

        # Case 4: Technical Interview Scheduled
        elif lifecycle.current_status == "TECHNICAL":
            existing_pending = any(
                f.status == "PENDING" and f.trigger_type == "TECHNICAL_INTERVIEW_PREP"
                for f in lifecycle.follow_up_recommendations
            )
            if existing_pending:
                return None

            return FollowUpRecommendation(
                id=str(uuid4()),
                lifecycle_id=lifecycle.id,
                user_id=lifecycle.user_id,
                trigger_type="TECHNICAL_INTERVIEW_PREP",
                status="PENDING",
                recommended_send_date=now,
                template_subject=f"Technical Interview Preparation: {role} at {company}",
                template_body=(
                    f"Technical round preparation for {role} at {company}:\n"
                    f"1. Highlight verified projects in autonomous agent orchestration and vector grounding.\n"
                    f"2. Be prepared to explain deterministic policy gates and evidence provenance."
                ),
            )

        # Case 5: Offer Received (trigger offer-analysis workflow)
        elif lifecycle.current_status == "OFFER":
            existing_pending = any(
                f.status == "PENDING" and f.trigger_type == "OFFER_ANALYSIS_WORKFLOW"
                for f in lifecycle.follow_up_recommendations
            )
            if existing_pending:
                return None

            return FollowUpRecommendation(
                id=str(uuid4()),
                lifecycle_id=lifecycle.id,
                user_id=lifecycle.user_id,
                trigger_type="OFFER_ANALYSIS_WORKFLOW",
                status="PENDING",
                recommended_send_date=now,
                template_subject=f"Offer Analysis & Negotiation Strategy: {company}",
                template_body=(
                    f"Congratulations on receiving an offer from {company} for {role}!\n\n"
                    f"CareerOS recommends evaluating the compensation package against current market percentiles "
                    f"and your stated profile salary preferences before signing. Draft negotiation talking points are available."
                ),
            )

        # Case 6: Rejected (trigger learning gap pattern analysis)
        elif lifecycle.current_status == "REJECTED":
            existing_pending = any(
                f.status == "PENDING" and f.trigger_type == "REJECTION_LEARNING_TRIGGER"
                for f in lifecycle.follow_up_recommendations
            )
            if existing_pending:
                return None

            return FollowUpRecommendation(
                id=str(uuid4()),
                lifecycle_id=lifecycle.id,
                user_id=lifecycle.user_id,
                trigger_type="REJECTION_LEARNING_TRIGGER",
                status="PENDING",
                recommended_send_date=now,
                template_subject=f"Learning Loop Trigger: Application to {company}",
                template_body=(
                    f"Application for {role} at {company} was closed. "
                    f"CareerOS Learning Agent will analyze requirement clusters to identify any recurring skill gaps "
                    f"and recommend high-signal coursework or project milestones."
                ),
            )

        return None
