"""
CareerOS 3-Agent Workflow
Agent 3: Auto Applier

Takes the genuine jobs verified by Agent 2, accesses the user's resume,
and constructs the application payload to automatically apply on the internal platform.
"""

import logging
from typing import Any

from apps.api.app.domain.job.models import CanonicalJob

logger = logging.getLogger("careeros.agent3_apply")

class AutoApplyAgent:
    """Agent 3: Fills details and applies to genuine jobs."""

    def apply_to_jobs(self, genuine_jobs: list[CanonicalJob], user_resume: dict[str, Any]) -> list[dict[str, Any]]:
        application_results = []
        for job in genuine_jobs:
            logger.info(f"Agent 3 preparing application for: {job.title} at {job.company_name}")
            payload = self._construct_application_payload(job, user_resume)
            
            # Simulate submitting the application to the internal job board
            result = self._submit_application(job, payload)
            application_results.append(result)
            
        return application_results

    def _construct_application_payload(self, job: CanonicalJob, user_resume: dict[str, Any]) -> dict[str, Any]:
        """Maps user resume data to the required job application fields."""
        return {
            "job_id": job.external_id,
            "applicant_name": user_resume.get("name", "Unknown User"),
            "applicant_email": user_resume.get("email", "user@example.com"),
            "skills": user_resume.get("skills", []),
            "experience_summary": user_resume.get("experience_summary", ""),
            "cover_letter": f"I am excited to apply for the {job.title} position at {job.company_name}."
        }

    def _submit_application(self, job: CanonicalJob, payload: dict[str, Any]) -> dict[str, Any]:
        """Mocks the internal API call to apply for the job."""
        logger.info(f"Successfully applied to {job.title} at {job.company_name}. Payload size: {len(str(payload))} bytes.")
        return {
            "job_id": job.external_id,
            "status": "APPLIED",
            "message": "Application submitted successfully."
        }

agent3_apply = AutoApplyAgent()
