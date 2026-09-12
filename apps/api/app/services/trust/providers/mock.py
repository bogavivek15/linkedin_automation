from datetime import datetime, timezone

from apps.api.app.domain.trust.models import (
    EvidenceCategory,
    EvidenceSentiment,
    EvidenceSeverity,
    TrustContext,
    TrustEvidence,
)
from apps.api.app.services.trust.providers.base import TrustEvidenceProvider


class MockEvidenceProvider(TrustEvidenceProvider):
    """
    Deterministic mock provider for offline tests and CI verification.
    Requires zero network calls, zero external API keys.
    """

    def __init__(self, mode: str = "AUTO"):
        self.mode = mode.upper()  # 'AUTO', 'CASE_A', 'CASE_B', 'CASE_C', 'CASE_D'

    @property
    def name(self) -> str:
        return "MOCK_EVIDENCE"

    async def collect(self, context: TrustContext) -> list[TrustEvidence]:
        now = datetime.now(timezone.utc)
        job = context.job
        company = (job.company_name or "").lower()

        # 1. Check explicit mode or infer from context
        if self.mode == "CASE_B" or "scam" in company or "fake" in company:
            return [
                TrustEvidence(
                    evidence_type=EvidenceCategory.PAYMENT_REQUEST.value,
                    source_name="Mock Registry",
                    source_url="https://mock-registry.test/flags",
                    claim="Company flagged for soliciting upfront registration fees",
                    sentiment=EvidenceSentiment.NEGATIVE,
                    severity=EvidenceSeverity.HIGH,
                    retrieved_at=now,
                ),
                TrustEvidence(
                    evidence_type=EvidenceCategory.PUBLIC_REPUTATION.value,
                    source_name="Consumer Protection Reports",
                    source_url=None,
                    claim="Multiple consumer complaints regarding fake employment offers",
                    sentiment=EvidenceSentiment.NEGATIVE,
                    severity=EvidenceSeverity.HIGH,
                    retrieved_at=now,
                ),
            ]

        if self.mode == "CASE_C" or "unknown" in company or "stealth" in company:
            return [
                TrustEvidence(
                    evidence_type=EvidenceCategory.MISSING_INFORMATION.value,
                    source_name="Mock Registry",
                    source_url=None,
                    claim="No registered corporate entity or public records found for this employer",
                    sentiment=EvidenceSentiment.NEUTRAL,
                    severity=EvidenceSeverity.LOW,
                    retrieved_at=now,
                )
            ]

        if self.mode == "CASE_D" or "conflicting" in company:
            return [
                TrustEvidence(
                    evidence_type=EvidenceCategory.COMPANY_IDENTITY.value,
                    source_name="Corporate Filing Registry",
                    source_url="https://filings.test/entity/123",
                    claim="Registered corporate business entity in good standing",
                    sentiment=EvidenceSentiment.POSITIVE,
                    severity=EvidenceSeverity.LOW,
                    retrieved_at=now,
                ),
                TrustEvidence(
                    evidence_type=EvidenceCategory.APPLICATION_DOMAIN.value,
                    source_name="Domain Threat Intelligence",
                    source_url=None,
                    claim="Application portal domain reported for phishing impersonation",
                    sentiment=EvidenceSentiment.NEGATIVE,
                    severity=EvidenceSeverity.HIGH,
                    retrieved_at=now,
                ),
            ]

        # Case A: Standard positive / verified catalog opportunity
        return [
            TrustEvidence(
                evidence_type=EvidenceCategory.PUBLIC_REPUTATION.value,
                source_name="OpenCorporates Registry",
                source_url="https://opencorporates.com/companies/verified",
                claim="Active registered legal entity in good standing",
                sentiment=EvidenceSentiment.POSITIVE,
                severity=EvidenceSeverity.LOW,
                retrieved_at=now,
            ),
            TrustEvidence(
                evidence_type=EvidenceCategory.APPLICATION_DOMAIN.value,
                source_name="Domain Intelligence",
                source_url=None,
                claim="Domain reputation score: 95/100 (Established corporate domain)",
                sentiment=EvidenceSentiment.POSITIVE,
                severity=EvidenceSeverity.LOW,
                retrieved_at=now,
            ),
        ]
