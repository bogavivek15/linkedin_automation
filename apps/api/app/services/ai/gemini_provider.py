"""
CareerOS — Gemini AI Provider.

Implements the AIProvider ABC using Google Gemini API for:
- Resume claim extraction
- Career profile analysis
- Chat/copilot responses
- Content generation

Falls back gracefully to MockAIProvider on API errors.
"""

import json
import re
from typing import Any
from uuid import UUID

import httpx

from apps.api.app.core.config import settings
from apps.api.app.core.logging import get_logger
from apps.api.app.domain.resume.models import ClaimType, ResumeClaim, SourceType
from apps.api.app.services.ai.provider import AIProvider

logger = get_logger(__name__)

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiProvider(AIProvider):
    """
    Production AI provider using Google Gemini API.
    Uses gemini-2.5-flash for fast, cost-effective inference.
    """

    def __init__(self, api_key: str | None = None, model: str = "gemini-2.5-flash"):
        self.api_key = api_key or settings.gemini_api_key
        self.model = model
        self._client = httpx.AsyncClient(timeout=30.0)

    async def _call_gemini(
        self,
        prompt: str,
        system_instruction: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> str:
        """
        Make a single Gemini API call. Returns the text response.
        Raises on HTTP or API errors.
        """
        url = f"{GEMINI_API_URL}/{self.model}:generateContent?key={self.api_key}"

        contents = [{"parts": [{"text": prompt}]}]

        body: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        if system_instruction:
            body["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        response = await self._client.post(url, json=body)
        response.raise_for_status()

        data = response.json()
        candidates = data.get("candidates", [])
        if not candidates:
            raise ValueError("Gemini returned no candidates")

        parts = candidates[0].get("content", {}).get("parts", [])
        if not parts:
            raise ValueError("Gemini returned empty content")

        return parts[0].get("text", "")

    async def extract_claims_proposal(
        self,
        resume_id: UUID,
        raw_text: str,
        sections: dict[str, str],
    ) -> list[ResumeClaim]:
        """
        Extract structured resume claims using Gemini.
        Each claim has a type, statement, source, evidence, and confidence.
        """
        system_instruction = """You are a precise resume analysis engine for CareerOS.
Extract structured claims from resume text. Each claim must be:
- Factual and directly evidenced by the resume text
- Classified by type: SKILL, METRIC, RESPONSIBILITY, CREDENTIAL, or OUTCOME
- Classified by source: EXPERIENCE, PROJECT, EDUCATION, or CERTIFICATION
- Assigned a confidence score between 0.0 and 1.0

CRITICAL RULES:
- Never fabricate claims not present in the resume
- Metrics must contain actual numbers from the text
- Skills must be explicitly mentioned, not inferred
- Confidence reflects how clearly the claim is stated

Respond ONLY with a JSON array of objects with these fields:
- claim_type: "SKILL" | "METRIC" | "RESPONSIBILITY" | "CREDENTIAL" | "OUTCOME"
- statement: string (the claim itself)
- source_type: "EXPERIENCE" | "PROJECT" | "EDUCATION" | "CERTIFICATION"
- evidence_text: string (exact quote or close paraphrase from resume)
- confidence_score: number (0.0-1.0)

Return at most 25 claims. Output ONLY valid JSON, no markdown fences."""

        # Build a concise prompt from sections
        section_text = ""
        for section_name, content in sections.items():
            if content.strip():
                section_text += f"\n--- {section_name} ---\n{content[:2000]}\n"

        if not section_text.strip():
            section_text = raw_text[:4000]

        prompt = f"Extract structured claims from this resume:\n{section_text}"

        try:
            response_text = await self._call_gemini(
                prompt=prompt,
                system_instruction=system_instruction,
                temperature=0.1,
                max_tokens=4096,
            )

            # Parse JSON response
            cleaned = response_text.strip()
            # Remove markdown code fences if present
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
                cleaned = re.sub(r"\s*```$", "", cleaned)

            claims_data = json.loads(cleaned)

            proposed_claims: list[ResumeClaim] = []
            for item in claims_data[:25]:
                claim_type: ClaimType = item.get("claim_type", "RESPONSIBILITY")
                if claim_type not in ("SKILL", "METRIC", "RESPONSIBILITY", "CREDENTIAL", "OUTCOME"):
                    claim_type = "RESPONSIBILITY"

                source_type: SourceType = item.get("source_type", "EXPERIENCE")
                if source_type not in ("PROJECT", "EXPERIENCE", "EDUCATION", "CERTIFICATION"):
                    source_type = "EXPERIENCE"

                confidence = float(item.get("confidence_score", 0.7))
                confidence = max(0.0, min(1.0, confidence))

                proposed_claims.append(
                    ResumeClaim(
                        resume_id=resume_id,
                        claim_type=claim_type,
                        statement=str(item.get("statement", ""))[:500],
                        source_type=source_type,
                        evidence_text=str(item.get("evidence_text", ""))[:500],
                        verification_status="UNCERTAIN",
                        confidence_score=confidence,
                        allowed_in_tailoring=False,
                    )
                )

            logger.info(
                "Gemini extracted %d claims from resume %s",
                len(proposed_claims),
                resume_id,
            )
            return proposed_claims

        except Exception as e:
            logger.warning("Gemini claim extraction failed: %s, falling back to deterministic extraction", str(e))
            return self._extract_claims_deterministic(resume_id, raw_text)

    def _extract_claims_deterministic(self, resume_id: UUID, raw_text: str) -> list[ResumeClaim]:
        claims: list[ResumeClaim] = []
        for line in raw_text.splitlines():
            line = line.strip()
            if not line or len(line) < 8:
                continue
            claim_type: ClaimType = "RESPONSIBILITY"
            if any(k in line.lower() for k in ("python", "fastapi", "react", "sql", "pytorch", "langgraph", "docker", "machine learning")):
                claim_type = "SKILL"
            elif any(c.isdigit() for c in line) and any(m in line.lower() for m in ("%", "x", "ms", "scale", "reduced", "increased")):
                claim_type = "METRIC"
            claims.append(
                ResumeClaim(
                    resume_id=resume_id,
                    claim_type=claim_type,
                    statement=line[:500],
                    source_type="EXPERIENCE",
                    evidence_text=line[:500],
                    verification_status="UNCERTAIN",
                    confidence_score=0.85,
                    allowed_in_tailoring=False,
                )
            )
            if len(claims) >= 20:
                break
        return claims

    async def generate_chat_response(
        self,
        messages: list[dict[str, str]],
        system_prompt: str,
        temperature: float = 0.4,
        max_tokens: int = 2048,
    ) -> str:
        """
        Generate a conversational response for the Career Copilot.
        """
        # Build conversation context
        conversation = "\n".join(
            f"{msg['role'].upper()}: {msg['content']}" for msg in messages
        )

        return await self._call_gemini(
            prompt=conversation,
            system_instruction=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    async def analyze_profile(
        self,
        profile_data: dict[str, Any],
        target_role: str | None = None,
    ) -> dict[str, Any]:
        """
        Analyze a career profile and return structured insights.
        """
        system_instruction = """You are the CareerOS Profile Analysis Agent.
Analyze the candidate's profile and provide actionable career intelligence.

Respond ONLY with a JSON object containing:
- profile_strength: number (0-100)
- strengths: string[] (top 3-5 strengths)
- weaknesses: string[] (top 3-5 areas for improvement)
- missing_skills: string[] (skills to acquire for target role)
- headline_suggestion: string (improved headline)
- summary_suggestion: string (improved career summary, 2-3 sentences)
- next_actions: string[] (top 3 actionable recommendations)
- experience_gaps: string[] (experience areas to develop)

Be specific and evidence-based. Reference actual profile data.
Output ONLY valid JSON, no markdown fences."""

        profile_summary = json.dumps(profile_data, indent=2, default=str)[:4000]
        prompt = f"Analyze this career profile"
        if target_role:
            prompt += f" for the target role: {target_role}"
        prompt += f"\n\nProfile Data:\n{profile_summary}"

        try:
            response_text = await self._call_gemini(
                prompt=prompt,
                system_instruction=system_instruction,
                temperature=0.3,
                max_tokens=2048,
            )

            cleaned = response_text.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
                cleaned = re.sub(r"\s*```$", "", cleaned)

            return json.loads(cleaned)

        except Exception as e:
            logger.error("Gemini profile analysis failed: %s", str(e))
            raise

    async def generate_content(
        self,
        topic: str,
        context: dict[str, Any],
        content_type: str = "linkedin_post",
    ) -> dict[str, Any]:
        """
        Generate professional content (posts, messages, etc.) grounded in career memory.
        """
        system_instruction = f"""You are the CareerOS Content Agent.
Generate a professional {content_type} about the given topic.

RULES:
- Content must be grounded in the provided career facts
- Never fabricate achievements or metrics
- Professional but authentic tone
- If content_type is linkedin_post: 150-300 words, use line breaks, include 2-3 relevant hashtags
- If content_type is connection_message: 50-100 words, personalized, professional

Respond ONLY with a JSON object containing:
- content: string (the generated content)
- title: string (optional title/hook)
- hashtags: string[] (for posts only)
- confidence: number (0-1, how well-grounded the content is)
- sources_used: string[] (which career facts were referenced)

Output ONLY valid JSON, no markdown fences."""

        context_str = json.dumps(context, indent=2, default=str)[:3000]
        prompt = f"Generate a {content_type} about: {topic}\n\nCareer Context:\n{context_str}"

        try:
            response_text = await self._call_gemini(
                prompt=prompt,
                system_instruction=system_instruction,
                temperature=0.6,
                max_tokens=1024,
            )

            cleaned = response_text.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
                cleaned = re.sub(r"\s*```$", "", cleaned)

            return json.loads(cleaned)

        except Exception as e:
            logger.error("Gemini content generation failed: %s", str(e))
            raise

    async def generate_roadmap(
        self,
        profile_data: dict[str, Any],
        target_role: str,
        timeline_months: int = 6,
    ) -> dict[str, Any]:
        """
        Generate a personalized career roadmap.
        """
        system_instruction = f"""You are the CareerOS Roadmap Agent.
Generate a personalized {timeline_months}-month career roadmap for reaching the target role.

Respond ONLY with a JSON object containing:
- target_role: string
- current_readiness: number (0-100)
- timeline_months: number
- milestones: array of objects with:
  - title: string
  - description: string
  - month: number (which month to complete by)
  - category: "SKILL" | "PROJECT" | "EXPERIENCE" | "CERTIFICATION" | "APPLICATION"
  - priority: "HIGH" | "MEDIUM" | "LOW"
  - resources: string[] (learning resources, max 2)
- skill_gaps: array of objects with:
  - skill: string
  - current_level: "NONE" | "BEGINNER" | "INTERMEDIATE" | "ADVANCED"
  - target_level: "INTERMEDIATE" | "ADVANCED" | "EXPERT"
  - priority: "HIGH" | "MEDIUM" | "LOW"

Be practical and specific. Max 8 milestones and 10 skill gaps.
Output ONLY valid JSON, no markdown fences."""

        profile_str = json.dumps(profile_data, indent=2, default=str)[:3000]
        prompt = f"Create a career roadmap to become a {target_role}.\n\nCurrent Profile:\n{profile_str}"

        try:
            response_text = await self._call_gemini(
                prompt=prompt,
                system_instruction=system_instruction,
                temperature=0.4,
                max_tokens=3000,
            )

            cleaned = response_text.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
                cleaned = re.sub(r"\s*```$", "", cleaned)

            return json.loads(cleaned)

        except Exception as e:
            logger.error("Gemini roadmap generation failed: %s", str(e))
            raise

    async def close(self):
        await self._client.aclose()
