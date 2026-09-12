from apps.api.app.domain.trust.models import (
    ConfidenceLevel,
    EvidenceCategory,
    EvidenceSentiment,
    EvidenceSeverity,
    RiskLevel,
    TrustAssessment,
    TrustContext,
    TrustEvidence,
)


class TrustPolicyEngine:
    """
    Deterministic rule engine that synthesizes collected evidence into
    reproducible trust scores, risk levels, and confidence ratings.
    Adheres strictly to the core invariant:
    AI proposes. Evidence validates. Rules decide. Humans control exceptions.
    """

    @classmethod
    def evaluate(
        cls,
        evidence: list[TrustEvidence],
        context: TrustContext,
        assessment_version: str = "v1",
    ) -> TrustAssessment:
        positive_signals: list[str] = []
        suspicious_signals: list[str] = []
        missing_information: list[str] = []

        has_severe_scam = False
        has_impersonation = False
        has_positive_evidence = False

        evidence_categories: set[str] = set()

        for ev in evidence:
            evidence_categories.add(ev.evidence_type)
            if ev.sentiment == EvidenceSentiment.POSITIVE:
                positive_signals.append(ev.claim)
                has_positive_evidence = True
            elif ev.sentiment == EvidenceSentiment.NEGATIVE:
                suspicious_signals.append(ev.claim)
                if ev.severity == EvidenceSeverity.HIGH:
                    if ev.evidence_type == EvidenceCategory.PAYMENT_REQUEST.value:
                        has_severe_scam = True
                    if ev.evidence_type == EvidenceCategory.IMPERSONATION.value:
                        has_impersonation = True
            elif ev.evidence_type == EvidenceCategory.MISSING_INFORMATION.value or ev.sentiment == EvidenceSentiment.NEUTRAL:
                missing_information.append(ev.claim)

        # 1. Base Score Calculation
        # Default neutral baseline for unknown is 50.0
        base_score = 50.0

        # Positive contributions (+12 per verified positive signal)
        pos_points = min(50.0, len(positive_signals) * 12.5)

        # Negative penalties
        neg_penalty = 0.0
        for ev in evidence:
            if ev.sentiment == EvidenceSentiment.NEGATIVE:
                if ev.severity == EvidenceSeverity.HIGH:
                    neg_penalty += 45.0
                elif ev.severity == EvidenceSeverity.MEDIUM:
                    neg_penalty += 20.0
                else:
                    neg_penalty += 10.0

        raw_trust_score = max(0.0, min(100.0, base_score + pos_points - neg_penalty))

        # 2. Hard Policy Gates (Overrides for critical threats)
        if has_severe_scam or has_impersonation:
            # Payment request or brand impersonation caps trust score at <= 20
            raw_trust_score = min(raw_trust_score, 18.0)

        # If zero positive signals and some negative signals, cap at 30
        if not has_positive_evidence and suspicious_signals:
            raw_trust_score = min(raw_trust_score, 30.0)

        # 3. Risk Score (Direct inverse scaled with severity)
        if has_severe_scam or has_impersonation:
            risk_score = 92.0
        else:
            risk_score = max(0.0, min(100.0, 100.0 - raw_trust_score))

        # 4. Confidence Level Calculation
        # High confidence requires multiple distinct evidence categories without strong conflict
        is_conflicting = has_positive_evidence and (has_severe_scam or has_impersonation)
        distinct_count = len(evidence_categories)

        if is_conflicting:
            confidence = ConfidenceLevel.LOW
        elif distinct_count >= 3 and len(positive_signals) + len(suspicious_signals) >= 3:
            confidence = ConfidenceLevel.HIGH
        elif distinct_count >= 2:
            confidence = ConfidenceLevel.MEDIUM
        else:
            confidence = ConfidenceLevel.LOW

        # 5. Risk Level Classification
        if has_severe_scam or has_impersonation or risk_score >= 65.0:
            risk_level = RiskLevel.HIGH
        elif confidence == ConfidenceLevel.LOW and not suspicious_signals:
            # Insufficient evidence -> UNKNOWN (distinct from LOW risk)
            risk_level = RiskLevel.UNKNOWN
        elif risk_score >= 35.0 or is_conflicting:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW

        # 6. Structured Explanation
        explanation = cls._generate_explanation(
            job_title=context.job.title,
            company_name=context.company_name,
            risk_level=risk_level,
            confidence=confidence,
            has_severe_scam=has_severe_scam,
            has_impersonation=has_impersonation,
            positive_signals=positive_signals,
            suspicious_signals=suspicious_signals,
            missing_information=missing_information,
        )

        return TrustAssessment(
            job_id=context.job.id,
            trust_score=round(raw_trust_score, 1),
            risk_score=round(risk_score, 1),
            risk_level=risk_level,
            confidence=confidence,
            positive_signals=positive_signals,
            suspicious_signals=suspicious_signals,
            missing_information=missing_information,
            evidence=evidence,
            explanation=explanation,
            assessment_version=assessment_version,
        )

    @classmethod
    def _generate_explanation(
        cls,
        job_title: str,
        company_name: str,
        risk_level: RiskLevel,
        confidence: ConfidenceLevel,
        has_severe_scam: bool,
        has_impersonation: bool,
        positive_signals: list[str],
        suspicious_signals: list[str],
        missing_information: list[str],
    ) -> str:
        parts: list[str] = []

        if risk_level == RiskLevel.HIGH:
            if has_severe_scam:
                parts.append(
                    f"CRITICAL WARNING: This posting for '{job_title}' at '{company_name}' contains explicit upfront payment or fee demands, which is a hallmark indicator of recruitment fraud."
                )
            elif has_impersonation:
                parts.append(
                    f"HIGH RISK: Suspected brand impersonation detected for '{company_name}'. The application domain does not match legitimate corporate infrastructure."
                )
            else:
                parts.append(
                    f"HIGH RISK: Multiple severe suspicious signals were identified for '{company_name}'."
                )
        elif risk_level == RiskLevel.UNKNOWN:
            parts.append(
                f"INSUFFICIENT EVIDENCE: CareerOS could not gather enough verifiable public records to confidently assess '{company_name}'."
            )
        elif risk_level == RiskLevel.MEDIUM:
            parts.append(
                f"MODERATE RISK: Opportunity for '{job_title}' presents minor domain or consistency concerns requiring candidate scrutiny."
            )
        else:
            parts.append(
                f"LOW RISK: Opportunity for '{job_title}' at '{company_name}' aligns with verified recruitment channels and established domain infrastructure."
            )

        if suspicious_signals:
            parts.append(f"Suspicious Indicators: {'; '.join(suspicious_signals[:3])}.")

        if positive_signals:
            parts.append(f"Verified Positive Factors: {'; '.join(positive_signals[:3])}.")

        if missing_information:
            parts.append(f"Information Gaps: {'; '.join(missing_information[:2])}.")

        parts.append(f"Assessment Confidence: {confidence.value}.")
        return " ".join(parts)
