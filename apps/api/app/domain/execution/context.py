"""
CareerOS Phase 11 — Execution Context.

Aggregates all relevant state required for evaluating safety gates,
authorizing execution modes, and assembling receipts.
"""

from typing import Any

from apps.api.app.domain.application.models import ApplicationPackage
from pydantic import BaseModel, Field


class ExecutionContext(BaseModel):
    """
    Context holding all relevant objects required to evaluate and execute an application.
    """

    user_id: str
    profile_id: str
    package: ApplicationPackage
    job: dict[str, Any] = Field(default_factory=dict)
    decision: dict[str, Any] | None = None
    trust_assessment: dict[str, Any] | None = None
    existing_execution: dict[str, Any] | None = None
    requested_mode: str | None = None

    def get_job_url(self) -> str:
        """Extract job application or posting URL."""
        return (
            self.job.get("application_url")
            or self.job.get("url")
            or self.job.get("apply_url")
            or "https://example.com/apply"
        )
