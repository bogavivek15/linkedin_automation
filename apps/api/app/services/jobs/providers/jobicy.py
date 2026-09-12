import asyncio
import logging
from typing import Any

import httpx
from apps.api.app.core.config import settings
from apps.api.app.core.errors import CareerOSError
from apps.api.app.domain.job.models import RawJobPayload
from apps.api.app.services.jobs.providers.base import JobProvider

logger = logging.getLogger("careeros.jobs.jobicy")


class JobicyProvider(JobProvider):
    """
    Public Jobicy Jobs API adapter.
    Endpoint: https://jobicy.com/api/v2/remote-jobs
    Requires ₹0 and zero API keys.
    """

    BASE_URL = "https://jobicy.com/api/v2/remote-jobs"

    @property
    def name(self) -> str:
        return "JOBICY"

    async def fetch_jobs(
        self,
        *,
        limit: int = 20,
        query: str | None = None,
        page: int = 1,
    ) -> list[RawJobPayload]:
        bounded_limit = min(max(1, limit), 50)
        params: dict[str, Any] = {"count": bounded_limit}

        if query and query.strip():
            # Jobicy accepts tag or industry
            params["tag"] = query.strip()

        retries = 3
        backoff = 0.5

        for attempt in range(1, retries + 1):
            try:
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(settings.job_provider_timeout_seconds),
                    headers={
                        "User-Agent": "CareerOS-JobIntelligence/1.0 (+https://careeros.dev/bot)",
                        "Accept": "application/json",
                    },
                ) as client:
                    response = await client.get(self.BASE_URL, params=params)

                if response.status_code == 200:
                    data = response.json()
                    raw_items = data.get("jobs", []) if isinstance(data, dict) else []
                    if not isinstance(raw_items, list):
                        raw_items = []

                    payloads: list[RawJobPayload] = []
                    for item in raw_items:
                        if not isinstance(item, dict):
                            continue
                        ext_id = str(
                            item.get("id") or item.get("jobSlug") or item.get("url") or ""
                        ).strip()
                        job_url = str(item.get("url") or "").strip()

                        if not ext_id:
                            continue

                        payloads.append(
                            RawJobPayload(
                                source=self.name,
                                external_id=ext_id,
                                source_url=job_url,
                                raw_data=item,
                            )
                        )
                    return payloads

                if response.status_code in (429, 502, 503, 504):
                    if attempt < retries:
                        await asyncio.sleep(backoff)
                        backoff *= 2
                        continue
                    raise CareerOSError(
                        code="JOB_PROVIDER_UNAVAILABLE",
                        message=f"Jobicy API returned status {response.status_code} after {retries} attempts",
                        status_code=502,
                    )

                raise CareerOSError(
                    code="JOB_PROVIDER_UNAVAILABLE",
                    message=f"Jobicy API returned unexpected status {response.status_code}",
                    status_code=502,
                )

            except httpx.TimeoutException:
                if attempt < retries:
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue
                raise CareerOSError(
                    code="JOB_PROVIDER_TIMEOUT",
                    message="Jobicy API timed out",
                    status_code=504,
                )
            except CareerOSError:
                raise
            except Exception as e:
                if attempt < retries:
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue
                raise CareerOSError(
                    code="JOB_PROVIDER_UNAVAILABLE",
                    message=f"Failed connecting to Jobicy API: {str(e)}",
                    status_code=502,
                )

        return []
