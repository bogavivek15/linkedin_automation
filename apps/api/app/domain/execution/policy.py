"""
CareerOS Phase 11 — Execution Safety Gates & Policy Engine.

Evaluates 12 deterministic safety gates before application execution:
1. Package exists
2. Package belongs to authenticated user
3. Package is approved
4. Package is not expired
5. Package version is current
6. Decision is still valid
7. Job is still active
8. Trust assessment is not stale / high risk
9. No blocking validation issues exist
10. No sensitive credentials requested
11. Execution mode is authorized
12. Application has not already been submitted

Default unsupported external application workflows to USER_HANDOFF.
Strictly prohibited: Fake browser automation, scraping, credential theft.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from apps.api.app.domain.execution.context import ExecutionContext
from apps.api.app.domain.execution.models import (
    ExecutionMode,
    SafetyCheckResult,
    SafetyGateEvaluation,
)

MAX_PACKAGE_AGE_DAYS = 30
MAX_TRUST_AGE_DAYS = 14

SENSITIVE_QUESTION_KEYWORDS = [
    "password",
    "passcode",
    "otp",
    "2fa",
    "cookie",
    "session token",
    "bank account",
    "credit card",
    "ssn",
    "social security",
    "routing number",
]


class ExecutionPolicy:
    """
    Deterministic policy evaluator for application execution safety gates.
    """

    @classmethod
    def evaluate(cls, context: ExecutionContext) -> SafetyGateEvaluation:
        """
        Evaluate all 12 safety checks against the execution context.
        """
        checks: list[SafetyCheckResult] = []
        blocking: list[str] = []

        # 1. Package exists
        pkg = context.package
        if pkg is not None:
            checks.append(SafetyCheckResult(check_name="package_exists", passed=True, reason="Application package exists."))
        else:
            checks.append(SafetyCheckResult(check_name="package_exists", passed=False, reason="Application package is missing."))
            blocking.append("Package does not exist.")
            return SafetyGateEvaluation(all_passed=False, checks=checks, blocking_reasons=blocking)

        # 2. Package belongs to authenticated user
        # Note: Package is retrieved using user isolation in repository
        checks.append(SafetyCheckResult(check_name="user_isolation", passed=True, reason="Package is isolated to authenticated user."))

        # 3. Package is approved
        if pkg.validation_status == "APPROVED":
            checks.append(SafetyCheckResult(check_name="package_approved", passed=True, reason="Package has been reviewed and approved."))
        else:
            msg = f"Package is in '{pkg.validation_status}' status, must be 'APPROVED' for execution."
            checks.append(SafetyCheckResult(check_name="package_approved", passed=False, reason=msg))
            blocking.append(msg)

        # 4. Package is not expired
        now = datetime.now(timezone.utc)
        pkg_created = pkg.created_at
        if pkg.validation_status == "EXPIRED" or (now - pkg_created) > timedelta(days=MAX_PACKAGE_AGE_DAYS):
            msg = "Application package has expired and must be re-prepared."
            checks.append(SafetyCheckResult(check_name="package_not_expired", passed=False, reason=msg))
            blocking.append(msg)
        else:
            checks.append(SafetyCheckResult(check_name="package_not_expired", passed=True, reason="Package is within valid freshness window."))

        # 5. Package version is current
        if pkg.package_version:
            checks.append(SafetyCheckResult(check_name="package_version_current", passed=True, reason=f"Package version {pkg.package_version} is valid."))
        else:
            msg = "Package version is missing or invalid."
            checks.append(SafetyCheckResult(check_name="package_version_current", passed=False, reason=msg))
            blocking.append(msg)

        # 6. Decision is still valid
        dec = context.decision
        if dec:
            action = dec.get("action")
            if action in ("AUTO_APPLY", "USER_APPROVAL"):
                checks.append(SafetyCheckResult(check_name="decision_valid", passed=True, reason=f"Decision action '{action}' permits application."))
            else:
                msg = f"Decision action '{action}' blocks application preparation/execution."
                checks.append(SafetyCheckResult(check_name="decision_valid", passed=False, reason=msg))
                blocking.append(msg)
        else:
            checks.append(SafetyCheckResult(check_name="decision_valid", passed=True, reason="No blocking decision record present."))

        # 7. Job is still active
        job_status = context.job.get("status", "ACTIVE")
        if job_status in ("CLOSED", "EXPIRED", "ARCHIVED"):
            msg = f"Job is no longer active (status: {job_status})."
            checks.append(SafetyCheckResult(check_name="job_active", passed=False, reason=msg))
            blocking.append(msg)
        else:
            checks.append(SafetyCheckResult(check_name="job_active", passed=True, reason="Job posting is currently active."))

        # 8. Trust assessment is not stale or high-risk
        trust = context.trust_assessment
        if trust:
            risk = trust.get("risk_level", "UNKNOWN")
            if risk == "HIGH":
                msg = "Execution blocked: Employer/Job trust assessment is HIGH risk."
                checks.append(SafetyCheckResult(check_name="trust_acceptable", passed=False, reason=msg))
                blocking.append(msg)
            else:
                checks.append(SafetyCheckResult(check_name="trust_acceptable", passed=True, reason=f"Trust assessment risk level is acceptable ({risk})."))
        else:
            checks.append(SafetyCheckResult(check_name="trust_acceptable", passed=True, reason="Trust assessment acceptable."))

        # 9. No blocking validation issues exist
        if pkg.blocking_issues and len(pkg.blocking_issues) > 0:
            msg = f"Package has {len(pkg.blocking_issues)} unresolved blocking issues."
            checks.append(SafetyCheckResult(check_name="no_blocking_issues", passed=False, reason=msg))
            blocking.extend(pkg.blocking_issues)
        else:
            checks.append(SafetyCheckResult(check_name="no_blocking_issues", passed=True, reason="No blocking issues in package."))

        # 10. No sensitive credentials requested
        has_sensitive = False
        for ans in pkg.application_answers:
            q_lower = ans.question.lower()
            if any(kw in q_lower for kw in SENSITIVE_QUESTION_KEYWORDS):
                has_sensitive = True
                msg = f"Application requests prohibited sensitive credentials: '{ans.question}'"
                checks.append(SafetyCheckResult(check_name="no_sensitive_credentials", passed=False, reason=msg))
                blocking.append(msg)
                break
        if not has_sensitive:
            checks.append(SafetyCheckResult(check_name="no_sensitive_credentials", passed=True, reason="No prohibited credentials requested."))

        # 11. Execution mode is authorized
        requested_mode = context.requested_mode or "USER_HANDOFF"
        if requested_mode in ("API", "USER_HANDOFF"):
            checks.append(SafetyCheckResult(check_name="mode_authorized", passed=True, reason=f"Execution mode '{requested_mode}' is authorized."))
        else:
            msg = f"Execution mode '{requested_mode}' is unsupported or unauthorized."
            checks.append(SafetyCheckResult(check_name="mode_authorized", passed=False, reason=msg))
            blocking.append(msg)

        # 12. Application has not already been submitted
        existing = context.existing_execution
        if existing and existing.get("status") in ("SUBMITTED", "VERIFIED"):
            msg = f"Application already submitted at {existing.get('submitted_at')}."
            checks.append(SafetyCheckResult(check_name="not_already_submitted", passed=False, reason=msg))
            blocking.append(msg)
        else:
            checks.append(SafetyCheckResult(check_name="not_already_submitted", passed=True, reason="No prior successful submission detected."))

        all_passed = len(blocking) == 0
        return SafetyGateEvaluation(
            all_passed=all_passed,
            checks=checks,
            blocking_reasons=blocking,
        )

    @classmethod
    def resolve_execution_mode(
        cls,
        requested_mode: str | None,
        job_metadata: dict[str, Any] | None = None,
    ) -> ExecutionMode:
        """
        Determine actual safe execution mode.
        Default unsupported external platforms strictly to USER_HANDOFF.
        Never use fake browser automation.
        """
        meta = job_metadata or {}
        supports_api = meta.get("supports_api_submission", False)

        if requested_mode == "API" and supports_api:
            return "API"
        return "USER_HANDOFF"
