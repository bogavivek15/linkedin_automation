from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from apps.api.app.core.config import settings
from apps.api.app.domain.trust.models import (
    ConfidenceLevel,
    EvidenceSentiment,
    EvidenceSeverity,
    RiskLevel,
    TrustAssessment,
    TrustEvidence,
)


class TrustRepository:
    """
    Repository for Trust & Safety assessments and evidence records.
    Provides in-memory transactional cache for ₹0 demo/test isolation.
    """

    _assessments: dict[str, dict[str, Any]] = {}  # job_id_str -> assessment_dict

    @classmethod
    def reset_store(cls) -> None:
        """Helper for test isolation."""
        cls._assessments.clear()

    @classmethod
    async def save_assessment(cls, assessment: TrustAssessment) -> TrustAssessment:
        job_id_str = str(assessment.job_id)
        now = datetime.now(timezone.utc).isoformat()

        evidence_dicts = [
            {
                "evidence_type": e.evidence_type,
                "source_name": e.source_name,
                "source_url": e.source_url,
                "claim": e.claim,
                "sentiment": e.sentiment.value,
                "severity": e.severity.value,
                "retrieved_at": e.retrieved_at.isoformat(),
            }
            for e in assessment.evidence
        ]

        doc = {
            "id": assessment.id,
            "job_id": assessment.job_id,
            "trust_score": assessment.trust_score,
            "risk_score": assessment.risk_score,
            "risk_level": assessment.risk_level.value,
            "confidence": assessment.confidence.value,
            "positive_signals": assessment.positive_signals,
            "suspicious_signals": assessment.suspicious_signals,
            "missing_information": assessment.missing_information,
            "evidence": evidence_dicts,
            "explanation": assessment.explanation,
            "assessment_version": assessment.assessment_version,
            "assessed_at": assessment.assessed_at.isoformat() if assessment.assessed_at else now,
        }

        cls._assessments[job_id_str] = doc
        return assessment

    @classmethod
    async def get_by_job_id(
        cls,
        job_id: UUID,
        ttl_hours: int | None = None,
    ) -> TrustAssessment | None:
        job_id_str = str(job_id)
        doc = cls._assessments.get(job_id_str)
        if not doc:
            return None

        # Check TTL cache expiration
        max_ttl = ttl_hours or settings.trust_assessment_ttl_hours
        assessed_at_dt = datetime.fromisoformat(doc["assessed_at"])
        age_hours = (datetime.now(timezone.utc) - assessed_at_dt).total_seconds() / 3600.0

        if age_hours > max_ttl:
            # Stale cache expired
            del cls._assessments[job_id_str]
            return None

        evidence_objects: list[TrustEvidence] = []
        for e in doc.get("evidence", []):
            evidence_objects.append(
                TrustEvidence(
                    evidence_type=e["evidence_type"],
                    source_name=e["source_name"],
                    source_url=e.get("source_url"),
                    claim=e["claim"],
                    sentiment=EvidenceSentiment(e.get("sentiment", "NEUTRAL")),
                    severity=EvidenceSeverity(e.get("severity", "LOW")),
                    retrieved_at=datetime.fromisoformat(e["retrieved_at"]),
                )
            )

        return TrustAssessment(
            id=doc["id"],
            job_id=doc["job_id"],
            trust_score=float(doc["trust_score"]),
            risk_score=float(doc["risk_score"]),
            risk_level=RiskLevel(doc["risk_level"]),
            confidence=ConfidenceLevel(doc["confidence"]),
            positive_signals=doc.get("positive_signals", []),
            suspicious_signals=doc.get("suspicious_signals", []),
            missing_information=doc.get("missing_information", []),
            evidence=evidence_objects,
            explanation=doc["explanation"],
            assessment_version=doc.get("assessment_version", "v1"),
            assessed_at=assessed_at_dt,
        )

    @classmethod
    async def delete_by_job_id(cls, job_id: UUID) -> None:
        job_id_str = str(job_id)
        cls._assessments.pop(job_id_str, None)
