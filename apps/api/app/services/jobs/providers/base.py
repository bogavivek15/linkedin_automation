from typing import Protocol, runtime_checkable

from apps.api.app.domain.job.models import RawJobPayload


@runtime_checkable
class JobProvider(Protocol):
    """
    Abstract Protocol for external job discovery adapters.
    No provider-specific schemas leak outside the adapter.
    """

    @property
    def name(self) -> str:
        """Provider name (e.g. 'HIMALAYAS', 'JOBICY', 'USER_SUBMISSION')."""
        ...

    async def fetch_jobs(
        self,
        *,
        limit: int = 20,
        query: str | None = None,
        page: int = 1,
    ) -> list[RawJobPayload]:
        """
        Fetch untrusted raw payloads from the provider.
        """
        ...
