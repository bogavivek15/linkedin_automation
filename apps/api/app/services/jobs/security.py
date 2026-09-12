from urllib.parse import urljoin

import httpx
from apps.api.app.core.config import settings
from apps.api.app.core.errors import CareerOSError
from apps.api.app.core.ssrf import validate_external_url


class SafeHttpClient:
    """
    SSRF-protected, redirect-aware HTTP client.
    - Disables automatic redirects to inspect and validate every redirect hop.
    - Validates scheme, hostname, and resolved IP on every hop.
    - Enforces timeout and maximum response byte limits.
    """

    def __init__(
        self,
        timeout_seconds: float | None = None,
        max_response_bytes: int | None = None,
        max_redirects: int = 5,
    ):
        self.timeout_seconds = timeout_seconds or settings.job_url_fetch_timeout_seconds
        self.max_response_bytes = max_response_bytes or settings.job_url_max_response_bytes
        self.max_redirects = max_redirects

    async def fetch_url(self, url: str) -> tuple[str, str]:
        """
        Fetch HTML or JSON content from a public URL safely.
        Returns: (content_str, final_url)
        Raises CareerOSError on unsafe URLs, redirect loops, timeouts, or oversized responses.
        """
        current_url = url
        redirect_count = 0

        async with httpx.AsyncClient(
            follow_redirects=False,
            timeout=httpx.Timeout(self.timeout_seconds),
            headers={
                "User-Agent": "CareerOS-JobIntelligence/1.0 (+https://careeros.dev/bot; legitimate public job analyzer)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.8,*/*;q=0.7",
            },
        ) as client:
            while redirect_count <= self.max_redirects:
                # 1. SSRF check on target URL
                ssrf_check = validate_external_url(current_url)
                if not ssrf_check.is_safe:
                    raise CareerOSError(
                        code="JOB_URL_UNSAFE",
                        message=f"Requested URL fails security validation: {ssrf_check.error}",
                        status_code=400,
                        details={"url": current_url, "error": ssrf_check.error},
                    )

                # 2. Issue request
                try:
                    response = await client.get(current_url)
                except httpx.TimeoutException:
                    raise CareerOSError(
                        code="JOB_PROVIDER_TIMEOUT",
                        message=f"Connection timed out while fetching {current_url}",
                        status_code=504,
                    )
                except Exception as e:
                    raise CareerOSError(
                        code="JOB_URL_FETCH_FAILED",
                        message=f"Failed to fetch job URL: {str(e)}",
                        status_code=502,
                    )

                # 3. Handle redirects manually
                if response.is_redirect:
                    location = response.headers.get("Location")
                    if not location:
                        raise CareerOSError(
                            code="JOB_URL_FETCH_FAILED",
                            message="Redirect response missing Location header",
                            status_code=502,
                        )
                    # Resolve relative redirect URLs
                    current_url = urljoin(current_url, location)
                    redirect_count += 1
                    continue

                # 4. Check status code
                if response.status_code in (401, 403):
                    raise CareerOSError(
                        code="USER_HANDOFF_REQUIRED",
                        message="Job URL requires authentication or login. Manual user access required.",
                        status_code=403,
                        details={"status_code": response.status_code},
                    )
                if response.status_code != 200:
                    raise CareerOSError(
                        code="JOB_URL_FETCH_FAILED",
                        message=f"Job page returned HTTP status {response.status_code}",
                        status_code=response.status_code if response.status_code < 500 else 502,
                    )

                # 5. Check response size limit
                content_bytes = response.content
                if len(content_bytes) > self.max_response_bytes:
                    raise CareerOSError(
                        code="JOB_URL_FETCH_FAILED",
                        message=f"Response exceeds maximum allowed size ({self.max_response_bytes} bytes)",
                        status_code=413,
                    )

                # 6. Decode text content
                return response.text, current_url

            raise CareerOSError(
                code="JOB_URL_FETCH_FAILED",
                message=f"Exceeded maximum allowed redirects ({self.max_redirects})",
                status_code=502,
            )
