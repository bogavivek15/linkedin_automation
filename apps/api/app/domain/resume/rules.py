import re

from apps.api.app.domain.resume.models import VerificationStatus

PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior)\s+instructions",
    r"system\s+prompt",
    r"give\s+me\s+(admin|administrator|root)",
    r"reveal\s+(api\s+key|password|secret|prompt)",
    r"bypass\s+security",
    r"disregard\s+(all\s+)?prior",
    r"you\s+are\s+now\s+in\s+developer\s+mode",
    r"add\s+[\"'].*[\"']\s+to\s+(the\s+)?candidate\s+profile",
    r"execute\s+command",
]

WEAK_INTEREST_PATTERNS = [
    r"interested\s+in",
    r"curious\s+about",
    r"familiar\s+with",
    r"learning\s+",
    r"hobbyist",
    r"aspiring\s+to",
]

INFLATION_PATTERNS = [
    r"expert(\s+in)?",
    r"mastery(\s+of)?",
    r"\b10\+?\s*years\b",
    r"senior\s+principal",
    r"world-class",
    r"authoritative",
]


class ClaimEvidenceValidator:
    """
    Deterministic evidence and grounding validator for resume claims.
    Principle: AI proposes. Evidence validates. Rules decide.
    """

    @classmethod
    def is_prompt_injection(cls, text: str) -> bool:
        """Detect prompt injection attempts in untrusted text."""
        lower_text = text.lower()
        for pattern in PROMPT_INJECTION_PATTERNS:
            if re.search(pattern, lower_text):
                return True
        return False

    @classmethod
    def is_grounded_in_text(cls, evidence: str, full_text: str) -> bool:
        """
        Verify that evidence text is grounded in the raw document text.
        Allows for minor whitespace / newline normalization differences.
        """
        if not evidence or not evidence.strip():
            return False

        # Extract core text from evidence if wrapped in quotes or prefix
        extracted_quote = evidence
        quote_match = re.search(r"['\"](.*?)['\"]", evidence)
        if quote_match:
            extracted_quote = quote_match.group(1)

        norm_evidence = re.sub(r"\s+", " ", extracted_quote.strip().lower())
        norm_full = re.sub(r"\s+", " ", full_text.strip().lower())

        if len(norm_evidence) < 4:
            return norm_evidence in norm_full

        # Direct containment check
        if norm_evidence in norm_full:
            return True

        # Check for substantial phrase containment (sliding window)
        words = norm_evidence.split()
        if len(words) >= 4:
            # Check 4-word sub-phrases
            for i in range(len(words) - 3):
                subphrase = " ".join(words[i : i + 4])
                if subphrase in norm_full:
                    return True

        return False

    @classmethod
    def evaluate_claim(
        cls,
        statement: str,
        evidence: str,
        full_text: str,
        candidate_source: str = "RESUME",
    ) -> tuple[VerificationStatus, float, bool]:
        """
        Evaluate a claim against its supporting evidence and document text.
        Returns:
            (verification_status, confidence_score, allowed_in_tailoring)
        """
        # 1. Guard against prompt injection or malicious directives
        if cls.is_prompt_injection(statement) or cls.is_prompt_injection(evidence):
            return "REJECTED", 0.0, False

        # 2. Strict evidence check
        if (
            not evidence
            or not evidence.strip()
            or evidence.strip().lower() in ("nothing", "none", "n/a")
        ):
            return "REJECTED", 0.0, False

        # 3. Grounding check against document text
        if not cls.is_grounded_in_text(evidence, full_text):
            # Evidence not found in source document
            return "REJECTED", 0.1, False

        # 4. Detect claim inflation / unsupported upgrades
        # (e.g. source says "Interested in Kubernetes", but claim says "Expert in Kubernetes")
        evidence_lower = evidence.lower()
        statement_lower = statement.lower()

        evidence_is_weak = any(re.search(p, evidence_lower) for p in WEAK_INTEREST_PATTERNS)
        statement_is_inflated = any(re.search(p, statement_lower) for p in INFLATION_PATTERNS)

        if evidence_is_weak and statement_is_inflated:
            # Inflation detected: cannot be verified or used in tailoring
            return "UNCERTAIN", 0.3, False

        if evidence_is_weak:
            # Weak interest stated, keep as INFERRED without tailoring allowance
            return "INFERRED", 0.6, False

        # 5. Assess semantic alignment between statement and evidence
        statement_words = set(re.findall(r"\w+", statement_lower))
        evidence_words = set(re.findall(r"\w+", evidence_lower))

        # Filter out common stop words
        stop_words = {
            "a",
            "an",
            "the",
            "and",
            "or",
            "in",
            "on",
            "at",
            "to",
            "for",
            "with",
            "of",
            "by",
            "is",
            "was",
        }
        meaningful_statement = statement_words - stop_words
        meaningful_evidence = evidence_words - stop_words

        if not meaningful_statement:
            return "UNCERTAIN", 0.4, False

        overlap = meaningful_statement.intersection(meaningful_evidence)
        overlap_ratio = len(overlap) / len(meaningful_statement)

        if overlap_ratio >= 0.60:
            # Explicitly supported by grounded evidence
            confidence = min(1.0, 0.85 + (overlap_ratio * 0.15))
            return "VERIFIED", round(confidence, 2), True
        elif overlap_ratio >= 0.35:
            # Reasonably inferred from evidence
            return "INFERRED", 0.70, False
        else:
            # Insufficient overlap between claim statement and cited evidence
            return "UNCERTAIN", 0.40, False
