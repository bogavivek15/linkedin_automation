"""
CareerOS 3-Agent Workflow
Agent 1: Job Matcher & Discovery.

Reads the uploaded user resume data and searches the internal database
for jobs matching their skills and experience. Collects job details.
"""

import hashlib
import logging
from typing import Any
from uuid import uuid4
from datetime import datetime, timezone

from apps.api.app.domain.job.models import CanonicalJob, EmploymentType, IngestionStatus, WorkMode
from apps.api.app.repositories.job_repository import JobRepository

logger = logging.getLogger("careeros.agent1_discovery")

def _description_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:32]

def _to_canonical(payload: dict[str, Any]) -> CanonicalJob:
    title = str(payload.get("title") or "Software Engineer")
    company = str(payload.get("company_name") or "Internal Corp")
    description = str(payload.get("description") or "")
    
    return CanonicalJob(
        external_id=str(uuid4()),
        source="INTERNAL_PLATFORM",
        source_url=str(payload.get("application_url") or "https://careeros.local/internal-apply"),
        title=title,
        normalized_title=title.lower().strip(),
        company_name=company,
        normalized_company=company.lower().strip(),
        description=description,
        description_hash=_description_hash(description),
        location=payload.get("location"),
        work_mode=WorkMode.REMOTE,
        employment_type=EmploymentType.FULL_TIME,
        salary_min=payload.get("salary_min"),
        salary_max=payload.get("salary_max"),
        is_paid=payload.get("is_paid", True),
        application_url=payload.get("application_url") or "https://careeros.local/internal-apply",
        required_skills=list(payload.get("required_skills") or []),
        ingestion_status=IngestionStatus.NORMALIZED,
    )

class JobMatcherAgent:
    """Agent 1: Ingests user resume, searches internal jobs, collects data."""
    
    def search_jobs(self, resume_data: dict[str, Any]) -> list[CanonicalJob]:
        user_skills = resume_data.get("skills", [])
        experience_years = resume_data.get("experience_years", 0)
        
        logger.info(f"Agent 1 searching jobs for user with skills: {user_skills} and exp: {experience_years}")
        
        # Simulating an internal DB search based on user skills
        jobs = self._mock_internal_db_search(user_skills, experience_years)
        return jobs

    async def persist_jobs(self, jobs: list[CanonicalJob]) -> list[CanonicalJob]:
        saved: list[CanonicalJob] = []
        for job in jobs:
            saved.append(await JobRepository.save_job(job))
        return saved

    def _mock_internal_db_search(self, skills: list[str], experience_years: float) -> list[CanonicalJob]:
        # Return some mock internal jobs, including one that might be a scam
        return [
            _to_canonical({
                "title": "Frontend Engineer",
                "company_name": "TechFlow Inc",
                "description": "Building modern React interfaces.",
                "location": "San Francisco, CA",
                "salary_min": 120000,
                "salary_max": 150000,
                "is_paid": True,
                "application_url": "https://careeros.local/jobs/techflow",
                "required_skills": ["React", "TypeScript"],
            }),
            _to_canonical({
                "title": "Software Engineering Intern",
                "company_name": "Apex Global Cloud Solutions",
                "description": "Remote internship. You must pay a $150 onboarding fee for training materials.",
                "location": "Remote",
                "salary_min": 0,
                "salary_max": 0,
                "is_paid": False,
                "application_url": "https://careeros.local/jobs/apex",
                "required_skills": ["Python"],
            }),
            _to_canonical({
                "title": "Backend Developer",
                "company_name": "DataServe LLC",
                "description": "API development with Python and FastAPI.",
                "location": "New York, NY",
                "salary_min": 140000,
                "salary_max": 170000,
                "is_paid": True,
                "application_url": "https://careeros.local/jobs/dataserve",
                "required_skills": ["Python", "FastAPI"],
            }),
        ]

agent1_discovery = JobMatcherAgent()
