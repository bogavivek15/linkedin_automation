"""
Tests for CareerOS Phase 4 Job Provider Health & Resilience.
"""

import pytest
from apps.api.app.services.jobs.service import JobIngestionService


@pytest.mark.asyncio
async def test_check_providers_health():
    health = await JobIngestionService.check_providers_health()
    assert health["overall_status"] in ("HEALTHY", "DEGRADED")
    assert "checked_at" in health
    assert "providers" in health

    providers = health["providers"]
    assert "HIMALAYAS" in providers
    assert "JOBICY" in providers

    himalayas = providers["HIMALAYAS"]
    assert himalayas["name"] == "HIMALAYAS"
    assert himalayas["status"] in ("HEALTHY", "DEGRADED")
    assert himalayas["latency_ms"] >= 0
    assert himalayas["timeout_seconds"] > 0
    assert himalayas["retry_limit"] == 3


@pytest.mark.asyncio
async def test_job_discovery_resilience_and_telemetry():
    summary = await JobIngestionService.run_discovery(limit=2)
    assert "total_jobs" in summary
    assert "providers" in summary
    assert "HIMALAYAS" in summary["providers"]
    assert "JOBICY" in summary["providers"]
