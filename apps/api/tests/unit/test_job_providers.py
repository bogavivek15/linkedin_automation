from unittest.mock import AsyncMock, patch

import pytest
from apps.api.app.core.errors import CareerOSError
from apps.api.app.domain.job.models import RawJobPayload
from apps.api.app.services.jobs.providers.himalayas import HimalayasProvider
from apps.api.app.services.jobs.providers.jobicy import JobicyProvider
from apps.api.app.services.jobs.providers.mock import (
    MockHimalayasProvider,
    MockJobicyProvider,
)
from apps.api.app.services.jobs.service import JobIngestionService


@pytest.mark.asyncio
async def test_mock_himalayas_provider_returns_bounded_payloads():
    provider = MockHimalayasProvider()
    assert provider.name == "HIMALAYAS"
    jobs = await provider.fetch_jobs(limit=1)
    assert len(jobs) == 1
    assert isinstance(jobs[0], RawJobPayload)
    assert jobs[0].source == "HIMALAYAS"
    assert jobs[0].external_id == "him-101"


@pytest.mark.asyncio
async def test_mock_jobicy_provider_returns_bounded_payloads():
    provider = MockJobicyProvider()
    assert provider.name == "JOBICY"
    jobs = await provider.fetch_jobs(limit=2)
    assert len(jobs) == 2
    assert jobs[0].source == "JOBICY"
    assert jobs[0].external_id == "jobicy-201"


@pytest.mark.asyncio
async def test_himalayas_provider_parses_valid_response():
    import httpx
    provider = HimalayasProvider()
    fake_json = {
        "jobs": [
            {
                "guid": "test-guid-1",
                "title": "Backend Python Developer",
                "companyName": "Acme AI Inc.",
                "description": "<p>Python and FastAPI</p>",
                "applicationLink": "https://acme.com/apply/1",
            }
        ]
    }

    mock_resp = httpx.Response(200, json=fake_json, request=httpx.Request("GET", "https://test"))

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
        payloads = await provider.fetch_jobs(limit=10)
        assert len(payloads) == 1
        assert payloads[0].external_id == "test-guid-1"
        assert payloads[0].source == "HIMALAYAS"
        assert payloads[0].source_url == "https://acme.com/apply/1"


@pytest.mark.asyncio
async def test_jobicy_provider_parses_valid_response():
    import httpx
    provider = JobicyProvider()
    fake_json = {
        "jobs": [
            {
                "id": "jobicy-999",
                "jobTitle": "React Frontend Engineer",
                "companyName": "Web Works LLC",
                "jobDescription": "<p>React, Next.js</p>",
                "url": "https://jobicy.com/jobs/react-frontend-engineer",
            }
        ]
    }

    mock_resp = httpx.Response(200, json=fake_json, request=httpx.Request("GET", "https://test"))

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
        payloads = await provider.fetch_jobs(limit=10)
        assert len(payloads) == 1
        assert payloads[0].external_id == "jobicy-999"
        assert payloads[0].source == "JOBICY"


@pytest.mark.asyncio
async def test_himalayas_provider_handles_missing_fields_gracefully():
    import httpx
    provider = HimalayasProvider()
    fake_json = [
        {"guid": "min-guid"}  # missing title, company, description, etc.
    ]

    mock_resp = httpx.Response(200, json=fake_json, request=httpx.Request("GET", "https://test"))

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
        payloads = await provider.fetch_jobs(limit=10)
        assert len(payloads) == 1
        assert payloads[0].external_id == "min-guid"


@pytest.mark.asyncio
async def test_himalayas_provider_retries_and_raises_on_503():
    import httpx
    provider = HimalayasProvider()
    mock_resp = httpx.Response(503, request=httpx.Request("GET", "https://test"))

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp), patch("asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(CareerOSError) as exc_info:
            await provider.fetch_jobs(limit=10)
        assert exc_info.value.code == "JOB_PROVIDER_UNAVAILABLE"


@pytest.mark.asyncio
async def test_provider_failure_isolation_in_discovery_service():
    """
    If Himalayas fails, Jobicy must still succeed and return results.
    """
    failing_himalayas = MockHimalayasProvider()
    failing_himalayas.fetch_jobs = AsyncMock(side_effect=CareerOSError(code="JOB_PROVIDER_UNAVAILABLE", message="Down"))

    succeeding_jobicy = MockJobicyProvider()

    with patch.object(JobIngestionService, "get_providers", return_value=[failing_himalayas, succeeding_jobicy]):
        summary = await JobIngestionService.run_discovery(provider_names=["HIMALAYAS", "JOBICY"])

        # Himalayas failed
        assert summary["providers"]["HIMALAYAS"]["status"] == "FAILED"
        assert summary["providers"]["HIMALAYAS"]["failed"] == 1

        # Jobicy succeeded
        assert summary["providers"]["JOBICY"]["status"] == "COMPLETED"
        assert summary["providers"]["JOBICY"]["fetched"] == 2
        assert len(summary["jobs"]) == 2
