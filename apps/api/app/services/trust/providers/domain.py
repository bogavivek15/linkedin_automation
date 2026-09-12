from datetime import datetime, timezone
from urllib.parse import urlparse

from apps.api.app.domain.trust.models import (
    EvidenceCategory,
    EvidenceSentiment,
    EvidenceSeverity,
    TrustContext,
    TrustEvidence,
)
from apps.api.app.services.trust.providers.base import TrustEvidenceProvider

LEGITIMATE_ATS_DOMAINS = {
    "greenhouse.io",
    "lever.co",
    "workable.com",
    "ashbyhq.com",
    "myworkdayjobs.com",
    "smartrecruiters.com",
    "bamboohr.com",
    "jobvite.com",
    "icims.com",
    "rippling.com",
    "himalayas.app",
    "jobicy.com",
}

MAJOR_TECH_COMPANIES = {
    "google": ["google.com", "alphabet.com"],
    "microsoft": ["microsoft.com", "linkedin.com"],
    "apple": ["apple.com"],
    "amazon": ["amazon.com", "amazon.jobs"],
    "meta": ["meta.com", "facebook.com"],
    "netflix": ["netflix.com"],
    "stripe": ["stripe.com"],
    "openai": ["openai.com"],
}

SUSPICIOUS_TLDS = {".xyz", ".top", ".buzz", ".work", ".click", ".link", ".online", ".site"}


class DomainEvidenceProvider(TrustEvidenceProvider):
    """
    Analyzes application and company domains for consistency,
    recognized ATS infrastructure, impersonation attempts, and protocol security.
    """

    @property
    def name(self) -> str:
        return "DOMAIN_EVIDENCE"

    async def collect(self, context: TrustContext) -> list[TrustEvidence]:
        evidence: list[TrustEvidence] = []
        job = context.job
        app_url = job.application_url or job.source_url
        now = datetime.now(timezone.utc)

        if not app_url:
            evidence.append(
                TrustEvidence(
                    evidence_type=EvidenceCategory.MISSING_INFORMATION.value,
                    source_name="CareerOS domain analysis",
                    source_url=None,
                    claim="No direct application URL provided",
                    sentiment=EvidenceSentiment.NEUTRAL,
                    severity=EvidenceSeverity.LOW,
                    retrieved_at=now,
                )
            )
            return evidence

        parsed = urlparse(app_url)
        hostname = (parsed.hostname or "").lower()

        # 1. Transport Security
        if parsed.scheme == "https":
            evidence.append(
                TrustEvidence(
                    evidence_type=EvidenceCategory.APPLICATION_DOMAIN.value,
                    source_name="CareerOS domain analysis",
                    source_url=app_url,
                    claim="Application link utilizes encrypted HTTPS transport",
                    sentiment=EvidenceSentiment.POSITIVE,
                    severity=EvidenceSeverity.LOW,
                    retrieved_at=now,
                )
            )
        else:
            evidence.append(
                TrustEvidence(
                    evidence_type=EvidenceCategory.APPLICATION_DOMAIN.value,
                    source_name="CareerOS domain analysis",
                    source_url=app_url,
                    claim="Insecure non-HTTPS transport detected on application link",
                    sentiment=EvidenceSentiment.NEGATIVE,
                    severity=EvidenceSeverity.MEDIUM,
                    retrieved_at=now,
                )
            )

        # 2. Check Recognized Enterprise ATS
        matched_ats = any(hostname == ats or hostname.endswith("." + ats) for ats in LEGITIMATE_ATS_DOMAINS)
        if matched_ats:
            evidence.append(
                TrustEvidence(
                    evidence_type=EvidenceCategory.APPLICATION_DOMAIN.value,
                    source_name="CareerOS domain analysis",
                    source_url=app_url,
                    claim=f"Application hosted on recognized verified recruitment platform ({hostname})",
                    sentiment=EvidenceSentiment.POSITIVE,
                    severity=EvidenceSeverity.LOW,
                    retrieved_at=now,
                )
            )

        # 3. Company vs Domain Alignment & Impersonation Check
        norm_company = job.normalized_company.lower()

        # Check for Major Company Impersonation
        for major_name, official_domains in MAJOR_TECH_COMPANIES.items():
            if major_name in norm_company:
                # If company name claims to be Google / Microsoft, check if domain belongs to official domains or verified ATS
                is_official = any(hostname == d or hostname.endswith("." + d) for d in official_domains)
                if not is_official and not matched_ats:
                    evidence.append(
                        TrustEvidence(
                            evidence_type=EvidenceCategory.IMPERSONATION.value,
                            source_name="CareerOS domain analysis",
                            source_url=app_url,
                            claim=f"High risk of brand impersonation: Posting claims to represent '{job.company_name}', but application domain '{hostname}' is not an official domain ({', '.join(official_domains)})",
                            sentiment=EvidenceSentiment.NEGATIVE,
                            severity=EvidenceSeverity.HIGH,
                            retrieved_at=now,
                        )
                    )

        # 4. Suspicious TLD on unverified domain
        if not matched_ats and any(hostname.endswith(tld) for tld in SUSPICIOUS_TLDS):
            evidence.append(
                TrustEvidence(
                    evidence_type=EvidenceCategory.DOMAIN.value,
                    source_name="CareerOS domain analysis",
                    source_url=app_url,
                    claim=f"Application domain utilizes high-abuse generic top-level domain ({hostname})",
                    sentiment=EvidenceSentiment.NEGATIVE,
                    severity=EvidenceSeverity.MEDIUM,
                    retrieved_at=now,
                )
            )

        # 5. Direct Domain Alignment (when company name appears in hostname)
        company_slug = "".join(c for c in norm_company if c.isalnum())
        if len(company_slug) >= 4 and company_slug in hostname.replace("-", "").replace(".", ""):
            evidence.append(
                TrustEvidence(
                    evidence_type=EvidenceCategory.COMPANY_IDENTITY.value,
                    source_name="CareerOS domain analysis",
                    source_url=app_url,
                    claim=f"Application domain '{hostname}' matches company identity '{job.company_name}'",
                    sentiment=EvidenceSentiment.POSITIVE,
                    severity=EvidenceSeverity.LOW,
                    retrieved_at=now,
                )
            )

        return evidence
