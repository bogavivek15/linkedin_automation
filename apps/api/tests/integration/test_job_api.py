from unittest.mock import patch
from uuid import uuid4

import pytest
from apps.api.app.main import app
from apps.api.app.repositories.job_repository import JobRepository
from httpx import ASGITransport, AsyncClient


@pytest.fixture(autouse=True)
def reset_jobs_store():
    JobRepository.reset_store()
    yield
    JobRepository.reset_store()


@pytest.mark.asyncio
async def test_job_discovery_endpoint_returns_normalized_jobs():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/jobs/discover",
            json={"providers": ["HIMALAYAS", "JOBICY"], "limit": 10},
            headers={"x-user-id": str(uuid4()), "x-user-role": "authenticated"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        summary = data["data"]
        assert summary["total_fetched"] == 4
        # him-101 and jobicy-201 represent a duplicate cross-provider opportunity!
        assert summary["total_deduplicated"] == 1
        assert summary["total_jobs"] == 4

        # Check job structure
        jobs = summary["jobs"]
        for j in jobs:
            assert "id" in j
            assert "title" in j
            assert "normalized_title" in j
            assert "company_name" in j
            assert "description" in j
            assert "description_hash" in j
            assert "work_mode" in j
            assert "employment_type" in j
            assert "ingestion_status" in j


@pytest.mark.asyncio
async def test_list_jobs_and_filter():
    user_id = str(uuid4())
    headers = {"x-user-id": user_id, "x-user-role": "authenticated"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Discover jobs first
        await client.post(
            "/api/v1/jobs/discover",
            json={"providers": ["HIMALAYAS"], "limit": 5},
            headers=headers,
        )

        # 2. List jobs
        list_resp = await client.get("/api/v1/jobs", headers=headers)
        assert list_resp.status_code == 200
        data = list_resp.json()["data"]
        assert data["total"] == 2
        assert len(data["jobs"]) == 2

        # 3. Filter by query
        filtered_resp = await client.get("/api/v1/jobs?query=python", headers=headers)
        assert filtered_resp.status_code == 200
        filtered_data = filtered_resp.json()["data"]
        assert filtered_data["total"] >= 1
        assert any("python" in j["title"].lower() for j in filtered_data["jobs"])


@pytest.mark.asyncio
async def test_import_public_job_url_with_json_ld():
    user_id = str(uuid4())
    headers = {"x-user-id": user_id, "x-user-role": "authenticated"}

    mock_html = """
    <html>
      <head>
        <script type="application/ld+json">
        {
          "@context": "https://schema.org/",
          "@type": "JobPosting",
          "title": "Staff Cloud Architect",
          "hiringOrganization": {
            "@type": "Organization",
            "name": "CloudSphere Technologies Inc."
          },
          "description": "<p>Looking for a Staff Architect with 8+ years experience. Requirements: AWS, Kubernetes, Terraform, Docker.</p>",
          "employmentType": "FULL_TIME",
          "jobLocation": {
            "@type": "Place",
            "address": "Remote"
          }
        }
        </script>
      </head>
      <body></body>
    </html>
    """

    with patch("apps.api.app.services.jobs.security.SafeHttpClient.fetch_url", return_value=(mock_html, "https://cloudspheretech.com/careers/staff-architect")):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/jobs/import-url",
                json={"url": "https://cloudspheretech.com/careers/staff-architect"},
                headers=headers,
            )

            assert resp.status_code == 200
            data = resp.json()["data"]
            job = data["job"]
            assert job["title"] == "Staff Cloud Architect"
            assert job["company_name"] == "CloudSphere Technologies Inc."
            assert job["normalized_company"] == "cloudsphere"
            assert "aws" in job["required_skills"]
            assert "kubernetes" in job["required_skills"]
            assert data["is_duplicate"] is False


@pytest.mark.asyncio
async def test_import_job_url_ssrf_rejection():
    headers = {"x-user-id": str(uuid4()), "x-user-role": "authenticated"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/jobs/import-url",
            json={"url": "http://127.0.0.1:8000/internal-admin"},
            headers=headers,
        )

        assert resp.status_code == 400
        error = resp.json()["error"]
        assert error["code"] == "JOB_URL_UNSAFE"


@pytest.mark.asyncio
async def test_cross_user_isolation_on_imported_jobs():
    user_a_id = str(uuid4())
    user_b_id = str(uuid4())

    headers_a = {"x-user-id": user_a_id, "x-user-role": "authenticated"}
    headers_b = {"x-user-id": user_b_id, "x-user-role": "authenticated"}

    mock_html = """
    <html>
      <head><title>Private Strategy Role at Secret Co</title></head>
      <body>Private internal opportunity description</body>
    </html>
    """

    with patch("apps.api.app.services.jobs.security.SafeHttpClient.fetch_url", return_value=(mock_html, "https://secretco.com/jobs/strategy")):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # User A imports private job
            import_resp = await client.post(
                "/api/v1/jobs/import-url",
                json={"url": "https://secretco.com/jobs/strategy"},
                headers=headers_a,
            )
            assert import_resp.status_code == 200
            job_a_id = import_resp.json()["data"]["job"]["id"]

            # User A can get it by ID
            get_resp_a = await client.get(f"/api/v1/jobs/{job_a_id}", headers=headers_a)
            assert get_resp_a.status_code == 200

            # User B CANNOT see it by ID (returns 404)
            get_resp_b = await client.get(f"/api/v1/jobs/{job_a_id}", headers=headers_b)
            assert get_resp_b.status_code == 404
            assert get_resp_b.json()["error"]["code"] == "JOB_NOT_FOUND"

            # User B's list does NOT include User A's private job
            list_resp_b = await client.get("/api/v1/jobs", headers=headers_b)
            jobs_b = list_resp_b.json()["data"]["jobs"]
            assert not any(j["id"] == job_a_id for j in jobs_b)


@pytest.mark.asyncio
async def test_get_nonexistent_job_returns_404():
    headers = {"x-user-id": str(uuid4()), "x-user-role": "authenticated"}
    fake_id = str(uuid4())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/api/v1/jobs/{fake_id}", headers=headers)
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "JOB_NOT_FOUND"
