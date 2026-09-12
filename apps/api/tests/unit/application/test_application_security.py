"""
Tests for Application Security and User Isolation.
"""

from uuid import uuid4

import pytest
from apps.api.app.core.errors import CareerOSError
from apps.api.app.domain.application.models import ApplicationPackage
from apps.api.app.repositories.application_repository import ApplicationRepository
from apps.api.app.services.application.service import ApplicationPreparationService


@pytest.mark.asyncio
async def test_cross_user_package_access_prevented():
    ApplicationRepository.reset_store()
    user_a = uuid4()
    user_b = uuid4()
    job_id = str(uuid4())

    pkg_a = ApplicationPackage(
        profile_id=str(uuid4()),
        job_id=job_id,
        resume_id=str(uuid4()),
        validation_status="READY_FOR_REVIEW",
    )
    await ApplicationRepository.save_package(pkg_a, user_a)

    # User A can access
    fetched_a = await ApplicationRepository.get_package(pkg_a.id, user_a)
    assert fetched_a is not None

    # User B cannot access
    fetched_b = await ApplicationRepository.get_package(pkg_a.id, user_b)
    assert fetched_b is None

    # User B cannot list User A's packages
    list_b = await ApplicationRepository.list_packages_for_user(user_b)
    assert len(list_b) == 0


@pytest.mark.asyncio
async def test_forged_profile_or_job_id_raises_404():
    service = ApplicationPreparationService()
    user = uuid4()
    forged_profile_id = uuid4()
    forged_job_id = uuid4()

    # Neither exists
    with pytest.raises(CareerOSError) as exc_info:
        await service.prepare_application(
            profile_id=forged_profile_id,
            job_id=forged_job_id,
            user_id=user,
        )
    assert exc_info.value.status_code == 404
