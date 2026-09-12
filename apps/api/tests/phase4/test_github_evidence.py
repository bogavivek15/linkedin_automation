"""
Tests for CareerOS Phase 4 GitHub Evidence Provider & Provenance Preservation.
"""

import pytest
from uuid import uuid4
from apps.api.app.services.integrations.github import GitHubEvidenceProvider
from apps.api.app.services.memory.service import MemoryService


@pytest.mark.asyncio
async def test_github_evidence_fetch():
    provider = GitHubEvidenceProvider()
    repos = await provider.fetch_user_repositories(username="bogavivek15")
    assert len(repos) >= 1
    sample = repos[0]
    assert sample.repo_name is not None
    assert sample.html_url.startswith("https://github.com/")
    assert sample.primary_language is not None


@pytest.mark.asyncio
async def test_github_evidence_ingestion_into_memory():
    user_id = uuid4()
    profile_id = uuid4()
    mem_service = MemoryService()

    provider = GitHubEvidenceProvider(memory_service=mem_service)
    records = await provider.ingest_into_career_memory(
        username="bogavivek15",
        user_id=user_id,
        profile_id=profile_id,
    )

    assert len(records) >= 1
    rec = records[0]
    assert rec.category == "PROJECT"
    # Verification status is EVIDENCE_VALIDATED with full provenance
    assert rec.verification_status == "EVIDENCE_VALIDATED"
    assert "GitHub Public Repository" in rec.provenance
    assert rec.source == "GITHUB_INTEGRATION"
