from typing import Protocol, runtime_checkable

from apps.api.app.domain.trust.models import TrustContext, TrustEvidence


@runtime_checkable
class TrustEvidenceProvider(Protocol):
    """
    Protocol for trust and safety evidence collectors.
    """

    @property
    def name(self) -> str:
        """Provider name (e.g. 'DETERMINISTIC_SIGNALS', 'DOMAIN_EVIDENCE', 'OPENCORPORATES', 'URLSCAN')."""
        ...

    async def collect(
        self,
        context: TrustContext,
    ) -> list[TrustEvidence]:
        """
        Collect structured evidence records for the given opportunity context.
        """
        ...
