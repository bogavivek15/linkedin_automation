"""
Unit tests for CareerOS Phase 11 Execution Service.
Tests idempotency, handoff coordination, user assertion receipts, and cancellation.
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from apps.api.app.domain.application.models import (
    ApplicationAnswer,
    ApplicationPackage,
    ApplicationQuality,
)
from apps.api.app.domain.job.models import CanonicalJob
from apps.api.app.repositories.application_repository import ApplicationRepository
from apps.api.app.repositories.execution_repository import ExecutionRepository
from apps.api.app.repositories.job_repository import JobRepository
from apps.api.app.services.execution.service import ExecutionService


@pytest.fixture(autouse=True)
def setup_stores():
    ExecutionRepository.reset_store()
    ApplicationRepository.reset_store()
    JobRepository._jobs.clear()


@pytest.fixture
def test_user_id() -> UUID:
    return UUID("11111111-1111-1111-1111-111111111111")


@pytest.fixture
def other_user_id() -> UUID:
    return UUID("22222222-2222-2222-2222-222222222222")


@pytest.fixture
async def approved_package(test_user_id: UUID) -> ApplicationPackage:
    job = CanonicalJob(
        id=uuid4(),
        source="greenhouse",
        source_url="https://techcorp.com/careers/apply",
        external_id="gh-101",
        title="Senior AI Engineer",
        normalized_title="senior ai engineer",
        company_name="TechCorp",
        normalized_company="techcorp",
        description="Build LLM orchestrators",
        description_hash="hash_101",
        application_url="https://techcorp.com/careers/apply",
        status="ACTIVE",
    )
    await JobRepository.save_job(job)

    pkg = ApplicationPackage(
        id=str(uuid4()),
        profile_id="prof-1",
        job_id=str(job.id),
        validation_status="APPROVED",
        quality_status="PASSED",
        cover_letter="Dear Hiring Team...",
        application_answers=[
            ApplicationAnswer(question="Years of Python experience?", answer="5 years"),
        ],
        quality=ApplicationQuality(
            relevance_score=95.0,
            completeness_score=90.0,
            clarity_score=90.0,
            consistency_score=90.0,
            claim_safety_score=100.0,
            requirement_coverage_score=95.0,
            overall_score=92.0,
        ),
        package_version="v1",
        created_at=datetime.now(timezone.utc),
    )
    await ApplicationRepository.save_package(pkg, test_user_id)
    return pkg


@pytest.mark.asyncio
async def test_execute_approved_package_creates_user_handoff(
    test_user_id: UUID, approved_package: ApplicationPackage
):
    service = ExecutionService()
    idemp_key = "idemp-001"

    exec_result = await service.execute_application(
        package_id=approved_package.id,
        user_id=test_user_id,
        idempotency_key=idemp_key,
        requested_mode="USER_HANDOFF",
    )

    assert exec_result.status == "USER_HANDOFF"
    assert exec_result.execution_mode == "USER_HANDOFF"
    assert exec_result.handoff_details is not None
    assert len(exec_result.handoff_details.checklist) > 0
    assert exec_result.receipt is not None


@pytest.mark.asyncio
async def test_repeated_execution_is_strictly_idempotent(
    test_user_id: UUID, approved_package: ApplicationPackage
):
    service = ExecutionService()
    idemp_key = "idemp-002"

    exec1 = await service.execute_application(
        package_id=approved_package.id,
        user_id=test_user_id,
        idempotency_key=idemp_key,
    )

    exec2 = await service.execute_application(
        package_id=approved_package.id,
        user_id=test_user_id,
        idempotency_key=idemp_key,
    )

    assert exec1.id == exec2.id
    assert exec1.idempotency_key == exec2.idempotency_key


@pytest.mark.asyncio
async def test_user_handoff_open_and_mark_submitted(
    test_user_id: UUID, approved_package: ApplicationPackage
):
    service = ExecutionService()
    exec_record = await service.execute_application(
        package_id=approved_package.id,
        user_id=test_user_id,
        idempotency_key="idemp-003",
    )

    # 1. Open external portal
    opened_exec = await service.record_handoff_opened(exec_record.id, test_user_id)
    assert opened_exec.handoff_details.opened_at is not None

    # 2. Mark as submitted by user
    submitted_exec = await service.mark_submitted(
        execution_id=exec_record.id,
        user_id=test_user_id,
        notes="Candidate confirmed external portal submission #CONF-42",
    )

    assert submitted_exec.status == "SUBMITTED"
    assert submitted_exec.receipt.is_user_assertion is True
    assert submitted_exec.receipt.evidence_type == "USER_ASSERTION"
    assert submitted_exec.notes == "Candidate confirmed external portal submission #CONF-42"

    # Verify audit events
    events = await service.get_audit_events(exec_record.id, test_user_id)
    event_types = [e.event_type for e in events]
    assert "EXECUTION_STARTED" in event_types
    assert "HANDOFF_CREATED" in event_types
    assert "HANDOFF_OPENED" in event_types
    assert "USER_MARKED_SUBMITTED" in event_types


@pytest.mark.asyncio
async def test_cancel_execution(test_user_id: UUID, approved_package: ApplicationPackage):
    service = ExecutionService()
    exec_record = await service.execute_application(
        package_id=approved_package.id,
        user_id=test_user_id,
        idempotency_key="idemp-004",
    )

    cancelled = await service.cancel_execution(
        execution_id=exec_record.id,
        user_id=test_user_id,
        reason="User decided not to apply",
    )

    assert cancelled.status == "CANCELLED"
    assert cancelled.failure_reason == "User decided not to apply"


@pytest.mark.asyncio
async def test_cross_user_isolation_blocks_access(
    test_user_id: UUID, other_user_id: UUID, approved_package: ApplicationPackage
):
    service = ExecutionService()
    exec_record = await service.execute_application(
        package_id=approved_package.id,
        user_id=test_user_id,
        idempotency_key="idemp-005",
    )

    # other_user cannot see or modify test_user's execution
    res = await service.get_execution(exec_record.id, other_user_id)
    assert res is None

    events = await service.get_audit_events(exec_record.id, other_user_id)
    assert len(events) == 0
