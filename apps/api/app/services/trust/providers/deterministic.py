import re
from datetime import datetime, timezone

from apps.api.app.domain.trust.models import (
    EvidenceCategory,
    EvidenceSentiment,
    EvidenceSeverity,
    TrustContext,
    TrustEvidence,
)
from apps.api.app.services.trust.providers.base import TrustEvidenceProvider

PAYMENT_PATTERNS = [
    (r"\b(must\s+pay|pay\s+\$?\d+).{0,80}(upfront|licensing|onboarding|software)\b", "Demands upfront payment for software or onboarding", EvidenceSeverity.HIGH),
    (r"\bupfront\s+(payment|fee|deposit)\b", "Demands an upfront fee or deposit", EvidenceSeverity.HIGH),
    (r"\b(registration\s+fee|application\s+fee|processing\s+fee)\b", "Demands upfront registration or processing fee", EvidenceSeverity.HIGH),
    (r"\b(training\s+fee|pay\s+for\s+training|paid\s+training\s+program)\b", "Requires candidate to pay training fee for job onboarding", EvidenceSeverity.HIGH),
    (r"\b(security\s+deposit|refundable\s+deposit)\b", "Demands security deposit to secure position", EvidenceSeverity.HIGH),
    (r"\b(pay\s+to\s+apply|pay\s+before\s+interview)\b", "Requires payment prior to application or interview", EvidenceSeverity.HIGH),
    (r"\b(wire\s+transfer|western\s+union|moneygram|crypto|cryptocurrency|gift\s+card|bitcoin)\b", "Mentions suspicious money transfer methods", EvidenceSeverity.HIGH),
]

SENSITIVE_INFO_PATTERNS = [
    (r"\b(bank\s+account\s+number|routing\s+number|credit\s+card|cvv)\b", "Requests financial or banking details in description", EvidenceSeverity.HIGH),
    (r"\b(upi\s+pin|atm\s+pin|otp|one\s+time\s+password)\b", "Mentions confidential PINs or OTP verification", EvidenceSeverity.HIGH),
    (r"\b(ssn|social\s+security\s+number|aadhaar\s+number)\s+(required\s+to\s+apply|upfront)\b", "Requests government ID or SSN upfront before offer", EvidenceSeverity.HIGH),
]

URGENCY_MANIPULATION_PATTERNS = [
    (r"\b(limited\s+seats|hurry\s+up|only\s+\d+\s+spots\s+left)\b", "Uses artificial scarcity or pressure tactics", EvidenceSeverity.MEDIUM),
    (r"\b(interview\s+on\s+telegram|interview\s+via\s+whatsapp|contact\s+on\s+telegram)\b", "Directs interview to informal messaging apps (Telegram/WhatsApp)", EvidenceSeverity.HIGH),
    (r"\b(no\s+interview\s+needed|immediate\s+offer\s+letter|guaranteed\s+job\s+placement)\b", "Promises guaranteed placement without formal interview", EvidenceSeverity.MEDIUM),
]

UNREALISTIC_COMP_PATTERNS = [
    (r"\b(\$?\d{4,}\s*(per\s*day|daily)|\$?\d{5,}\s*(per\s*week|weekly))\b", "Advertises suspiciously inflated short-term compensation", EvidenceSeverity.HIGH),
    (r"\b(earn\s+\$?\d{4,}\s+from\s+home\s+with\s+no\s+skills)\b", "Promises high earnings without necessary skills or experience", EvidenceSeverity.HIGH),
]


class DeterministicEvidenceProvider(TrustEvidenceProvider):
    """
    Deterministic rule-based evidence collector.
    Analyzes job description and context for suspicious linguistic patterns,
    payment demands, sensitive data harvesting, and job quality signals.
    """

    @property
    def name(self) -> str:
        return "DETERMINISTIC_SIGNALS"

    async def collect(self, context: TrustContext) -> list[TrustEvidence]:
        evidence: list[TrustEvidence] = []
        job = context.job
        desc = (job.description or "").lower()
        now = datetime.now(timezone.utc)

        # 1. Payment Requests
        for pattern, claim, severity in PAYMENT_PATTERNS:
            if re.search(pattern, desc, re.IGNORECASE):
                evidence.append(
                    TrustEvidence(
                        evidence_type=EvidenceCategory.PAYMENT_REQUEST.value,
                        source_name="CareerOS deterministic analysis",
                        source_url=None,
                        claim=claim,
                        sentiment=EvidenceSentiment.NEGATIVE,
                        severity=severity,
                        retrieved_at=now,
                    )
                )

        # 2. Sensitive Information Requests
        for pattern, claim, severity in SENSITIVE_INFO_PATTERNS:
            if re.search(pattern, desc, re.IGNORECASE):
                evidence.append(
                    TrustEvidence(
                        evidence_type=EvidenceCategory.SENSITIVE_INFORMATION.value,
                        source_name="CareerOS deterministic analysis",
                        source_url=None,
                        claim=claim,
                        sentiment=EvidenceSentiment.NEGATIVE,
                        severity=severity,
                        retrieved_at=now,
                    )
                )

        # 3. Urgency & Informal Messaging Manipulation
        for pattern, claim, severity in URGENCY_MANIPULATION_PATTERNS:
            if re.search(pattern, desc, re.IGNORECASE):
                evidence.append(
                    TrustEvidence(
                        evidence_type=EvidenceCategory.URGENCY.value,
                        source_name="CareerOS deterministic analysis",
                        source_url=None,
                        claim=claim,
                        sentiment=EvidenceSentiment.NEGATIVE,
                        severity=severity,
                        retrieved_at=now,
                    )
                )

        # 4. Unrealistic Compensation
        for pattern, claim, severity in UNREALISTIC_COMP_PATTERNS:
            if re.search(pattern, desc, re.IGNORECASE):
                evidence.append(
                    TrustEvidence(
                        evidence_type=EvidenceCategory.COMPENSATION.value,
                        source_name="CareerOS deterministic analysis",
                        source_url=None,
                        claim=claim,
                        sentiment=EvidenceSentiment.NEGATIVE,
                        severity=severity,
                        retrieved_at=now,
                    )
                )

        # 5. Positive Job Quality Signals
        if len(desc) > 300 and not any(e.severity == EvidenceSeverity.HIGH for e in evidence):
            evidence.append(
                TrustEvidence(
                    evidence_type=EvidenceCategory.JOB_DESCRIPTION.value,
                    source_name="CareerOS deterministic analysis",
                    source_url=None,
                    claim="Job description contains comprehensive professional details and structured context",
                    sentiment=EvidenceSentiment.POSITIVE,
                    severity=EvidenceSeverity.LOW,
                    retrieved_at=now,
                )
            )

        if job.required_skills and len(job.required_skills) >= 2:
            evidence.append(
                TrustEvidence(
                    evidence_type=EvidenceCategory.JOB_CONSISTENCY.value,
                    source_name="CareerOS deterministic analysis",
                    source_url=None,
                    claim=f"Lists verifiable technical skills: {', '.join(job.required_skills[:4])}",
                    sentiment=EvidenceSentiment.POSITIVE,
                    severity=EvidenceSeverity.LOW,
                    retrieved_at=now,
                )
            )

        if job.salary_min and job.salary_max and 20000 <= job.salary_min <= 500000:
            evidence.append(
                TrustEvidence(
                    evidence_type=EvidenceCategory.COMPENSATION.value,
                    source_name="CareerOS deterministic analysis",
                    source_url=None,
                    claim=f"Realistic explicit compensation range specified (${int(job.salary_min):,} - ${int(job.salary_max):,} {job.salary_currency})",
                    sentiment=EvidenceSentiment.POSITIVE,
                    severity=EvidenceSeverity.LOW,
                    retrieved_at=now,
                )
            )

        return evidence
