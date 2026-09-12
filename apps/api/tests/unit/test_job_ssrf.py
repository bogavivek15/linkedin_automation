from unittest.mock import AsyncMock, patch

import pytest
from apps.api.app.core.errors import CareerOSError
from apps.api.app.core.ssrf import validate_external_url
from apps.api.app.services.jobs.security import SafeHttpClient


def test_ssrf_validator_blocks_internal_and_cloud_metadata():
    assert validate_external_url("http://127.0.0.1:8000").is_safe is False
    assert validate_external_url("http://localhost:3000").is_safe is False
    assert validate_external_url("http://169.254.169.254/latest/meta-data/").is_safe is False
    assert validate_external_url("http://10.0.0.5/api").is_safe is False
    assert validate_external_url("http://192.168.1.1").is_safe is False
    assert validate_external_url("http://172.16.0.1").is_safe is False
    assert validate_external_url("file:///etc/passwd").is_safe is False
    assert validate_external_url("gopher://evil.com").is_safe is False


@pytest.mark.asyncio
async def test_safe_http_client_blocks_direct_private_url():
    client = SafeHttpClient()
    with pytest.raises(CareerOSError) as exc_info:
        await client.fetch_url("http://127.0.0.1:8080/secret")
    assert exc_info.value.code == "JOB_URL_UNSAFE"


@pytest.mark.asyncio
async def test_safe_http_client_blocks_redirect_to_private_ip():
    """
    Simulate a public URL that returns a 302 redirecting to http://127.0.0.1:8080
    SafeHttpClient must catch the redirect target and abort immediately.
    """
    client = SafeHttpClient()

    redirect_resp = AsyncMock()
    redirect_resp.is_redirect = True
    redirect_resp.headers = {"Location": "http://127.0.0.1:8080/internal"}
    redirect_resp.status_code = 302

    with patch("httpx.AsyncClient.get", return_value=redirect_resp):
        with pytest.raises(CareerOSError) as exc_info:
            await client.fetch_url("https://public-job-site.com/apply")

        assert exc_info.value.code == "JOB_URL_UNSAFE"
        assert "fails security validation" in exc_info.value.message


@pytest.mark.asyncio
async def test_safe_http_client_enforces_max_response_size():
    client = SafeHttpClient(max_response_bytes=100)

    oversized_resp = AsyncMock()
    oversized_resp.is_redirect = False
    oversized_resp.status_code = 200
    oversized_resp.content = b"x" * 200  # 200 bytes > 100 bytes limit
    oversized_resp.text = "x" * 200

    with patch("httpx.AsyncClient.get", return_value=oversized_resp):
        with pytest.raises(CareerOSError) as exc_info:
            await client.fetch_url("https://legit-jobs.com/post")

        assert exc_info.value.code == "JOB_URL_FETCH_FAILED"
        assert exc_info.value.status_code == 413
