"""
CareerOS 3-Agent Workflow
Agent 2: Trust & Safety Agent

Evaluates the jobs collected by Agent 1. Uses Gemini to determine if a job
is genuine or a scam based on company details, job description, and payment requests.
Only genuine jobs are saved and passed to Agent 3.
"""

import json
import logging
from typing import Any

from apps.api.app.domain.gemini_client import genai_types, get_gemini_client
from apps.api.app.domain.job.models import CanonicalJob

logger = logging.getLogger("careeros.agent2_trust")

class JobTrustAgent:
    """Agent 2: Verifies if a job is genuine or a scam using Gemini."""
    
    def evaluate_jobs(self, jobs: list[CanonicalJob]) -> list[CanonicalJob]:
        genuine_jobs = []
        for job in jobs:
            logger.info(f"Agent 2 evaluating job: {job.title} at {job.company_name}")
            is_genuine = self._check_if_genuine(job)
            if is_genuine:
                genuine_jobs.append(job)
            else:
                logger.warning(f"Job {job.title} at {job.company_name} flagged as SCAM. Discarding.")
        
        return genuine_jobs

    def _check_if_genuine(self, job: CanonicalJob) -> bool:
        client = get_gemini_client()
        if client is None or genai_types is None:
            # If Gemini isn't available, we might default to True or False depending on strictness.
            # We'll default to True for the sake of the mock, but log a warning.
            logger.warning("Gemini unavailable; Trust Agent defaulting to Genuine.")
            return True

        prompt = f"""
You are the CareerOS Trust & Safety Agent. 
Evaluate the following job posting and determine if it is a genuine opportunity or a scam.
Red flags for scams include: 
- Upfront payment demands for onboarding or software.
- Requests for sensitive information (SSN, banking) in the JD.
- Unrealistic compensation for the role.

Company Name: {job.company_name}
Job Title: {job.title}
Job Description: {job.description[:1000]}
Paid/Unpaid: {"Paid" if job.is_paid else "Unpaid"}

Respond with a JSON object exactly like this:
{{
    "is_genuine": true/false,
    "reason": "explanation of your decision"
}}
"""
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    temperature=0.1,
                ),
            )
            data = json.loads(response.text or "{}")
            return bool(data.get("is_genuine", False))
        except Exception as exc:
            logger.error(f"Gemini trust verification failed for job {job.id}: {exc}")
            # If evaluation fails, fail closed (discard) or fail open (keep)?
            # For safety, fail closed.
            return False

agent2_trust = JobTrustAgent()
