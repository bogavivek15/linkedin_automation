import re
from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from apps.api.app.domain.resume.models import ClaimType, ResumeClaim


class AIProvider(ABC):
    """
    Abstract base class for AI providers.
    All agents consume this interface — never a concrete provider directly.
    """

    @abstractmethod
    async def extract_claims_proposal(
        self,
        resume_id: UUID,
        raw_text: str,
        sections: dict[str, str],
    ) -> list[ResumeClaim]:
        """Propose structured claims with evidence from resume sections."""
        pass

    async def generate_chat_response(
        self,
        messages: list[dict[str, str]],
        system_prompt: str,
        temperature: float = 0.4,
        max_tokens: int = 2048,
    ) -> str:
        """Generate a conversational response. Override in LLM providers."""
        raise NotImplementedError("Chat not supported by this provider")

    async def analyze_profile(
        self,
        profile_data: dict[str, Any],
        target_role: str | None = None,
    ) -> dict[str, Any]:
        """Analyze a career profile and return structured insights."""
        raise NotImplementedError("Profile analysis not supported by this provider")

    async def generate_content(
        self,
        topic: str,
        context: dict[str, Any],
        content_type: str = "linkedin_post",
    ) -> dict[str, Any]:
        """Generate professional content grounded in career data."""
        raise NotImplementedError("Content generation not supported by this provider")

    async def generate_roadmap(
        self,
        profile_data: dict[str, Any],
        target_role: str,
        timeline_months: int = 6,
    ) -> dict[str, Any]:
        """Generate a personalized career roadmap."""
        raise NotImplementedError("Roadmap generation not supported by this provider")


class MockAIProvider(AIProvider):
    """
    Deterministic rule-based AI provider for testing and zero-network local execution.
    Generates structured claim proposals from extracted section text.
    """

    async def extract_claims_proposal(
        self,
        resume_id: UUID,
        raw_text: str,
        sections: dict[str, str],
    ) -> list[ResumeClaim]:
        proposed_claims: list[ResumeClaim] = []

        # 1. Experience lines
        if "EXPERIENCE" in sections:
            lines = [
                line.strip()
                for line in sections["EXPERIENCE"].splitlines()
                if len(line.strip()) > 15
            ]
            for line in lines[:8]:
                # Determine claim type
                claim_type: ClaimType = "RESPONSIBILITY"
                if any(char in line for char in ["%", "$"]) or re.search(
                    r"\b\d+(\.\d+)?\s*(k|m|x|%|hours|users|ms)\b", line, re.IGNORECASE
                ):
                    claim_type = "METRIC"
                elif any(
                    action in line.lower()
                    for action in [
                        "increased",
                        "reduced",
                        "delivered",
                        "built",
                        "architected",
                        "engineered",
                        "achieved",
                    ]
                ):
                    claim_type = "OUTCOME"

                statement = re.sub(r"^[\s•\-*]+", "", line).strip()
                proposed_claims.append(
                    ResumeClaim(
                        resume_id=resume_id,
                        claim_type=claim_type,
                        statement=statement,
                        source_type="EXPERIENCE",
                        evidence_text=f"Experience excerpt: '{line}'",
                        verification_status="UNCERTAIN",
                        confidence_score=0.80,
                        allowed_in_tailoring=False,
                    )
                )

        # 2. Projects lines
        if "PROJECTS" in sections:
            lines = [
                line.strip() for line in sections["PROJECTS"].splitlines() if len(line.strip()) > 15
            ]
            for line in lines[:6]:
                statement = re.sub(r"^[\s•\-*]+", "", line).strip()
                proposed_claims.append(
                    ResumeClaim(
                        resume_id=resume_id,
                        claim_type="OUTCOME"
                        if any(char.isdigit() for char in line)
                        else "RESPONSIBILITY",
                        statement=statement,
                        source_type="PROJECT",
                        evidence_text=f"Project excerpt: '{line}'",
                        verification_status="UNCERTAIN",
                        confidence_score=0.85,
                        allowed_in_tailoring=False,
                    )
                )

        # 3. Education lines
        if "EDUCATION" in sections:
            lines = [
                line.strip() for line in sections["EDUCATION"].splitlines() if len(line.strip()) > 5
            ]
            for line in lines[:3]:
                statement = re.sub(r"^[\s•\-*]+", "", line).strip()
                proposed_claims.append(
                    ResumeClaim(
                        resume_id=resume_id,
                        claim_type="CREDENTIAL",
                        statement=statement,
                        source_type="EDUCATION",
                        evidence_text=f"Education excerpt: '{line}'",
                        verification_status="UNCERTAIN",
                        confidence_score=0.90,
                        allowed_in_tailoring=False,
                    )
                )

        # 4. Skills extraction
        if "SKILLS" in sections:
            raw_skills = sections["SKILLS"]
            tokens = re.split(r"[,|\n•/]", raw_skills)
            for token in tokens:
                clean_skill = re.sub(r"^[\s•\-*]+", "", token).strip()
                if 2 <= len(clean_skill) <= 35 and not any(
                    h in clean_skill.lower() for h in ["skills", "technical"]
                ):
                    proposed_claims.append(
                        ResumeClaim(
                            resume_id=resume_id,
                            claim_type="SKILL",
                            statement=f"Proficient in {clean_skill}",
                            source_type="EXPERIENCE",
                            evidence_text=f"Skills excerpt: '{clean_skill}'",
                            verification_status="UNCERTAIN",
                            confidence_score=0.85,
                            allowed_in_tailoring=False,
                        )
                    )
                    if len(proposed_claims) >= 25:
                        break

        return proposed_claims

    async def generate_chat_response(
        self,
        messages: list[dict[str, str]],
        system_prompt: str,
        temperature: float = 0.4,
        max_tokens: int = 2048,
    ) -> str:
        """Deterministic mock chat response for offline/demo mode."""
        last_message = messages[-1]["content"] if messages else ""
        lower = last_message.lower()

        if "profile" in lower or "strength" in lower:
            return (
                "Based on your profile, I can see strong skills in Python, FastAPI, and PostgreSQL. "
                "Your profile completeness is at 82%. To strengthen it further, I recommend:\n\n"
                "1. **Add 2 backend projects** showcasing distributed systems experience\n"
                "2. **Update your headline** to highlight your target role\n"
                "3. **Add Docker and Kubernetes** to your skills — these appear in 78% of your target job postings\n\n"
                "Would you like me to help with any of these?"
            )
        elif "job" in lower or "match" in lower or "apply" in lower:
            return (
                "I found **14 matching opportunities** for your profile. Here are the top 3:\n\n"
                "1. **AI Platform Engineer** at Anthropic — 96% match\n"
                "2. **Backend Engineer** at Stripe — 89% match\n"
                "3. **Systems Engineer** at Cloudflare — 85% match\n\n"
                "Would you like me to prepare an application for any of these?"
            )
        elif "roadmap" in lower or "plan" in lower or "become" in lower:
            return (
                "Here's your personalized career roadmap:\n\n"
                "**Month 1-2:** Complete Docker & Kubernetes fundamentals\n"
                "**Month 2-3:** Build a distributed systems project\n"
                "**Month 3-4:** Contribute to an open-source backend project\n"
                "**Month 4-5:** Start applying to target roles\n"
                "**Month 5-6:** Interview preparation and networking\n\n"
                "Want me to create detailed milestones for each phase?"
            )
        else:
            return (
                "I'm your CareerOS Copilot. I can help you with:\n\n"
                "• **Profile Analysis** — Understand your strengths and gaps\n"
                "• **Job Matching** — Find roles that fit your skills\n"
                "• **Application Prep** — Tailored resumes and cover letters\n"
                "• **Career Roadmap** — Personalized growth plan\n"
                "• **Content Creation** — Professional posts and messages\n\n"
                "What would you like to work on?"
            )

    async def analyze_profile(
        self,
        profile_data: dict[str, Any],
        target_role: str | None = None,
    ) -> dict[str, Any]:
        """Deterministic mock profile analysis."""
        return {
            "profile_strength": 82,
            "strengths": [
                "Strong Python and backend development skills",
                "Experience with REST API design",
                "PostgreSQL and database expertise",
            ],
            "weaknesses": [
                "Limited container orchestration experience",
                "No public open-source contributions visible",
                "Career summary could be more specific",
            ],
            "missing_skills": ["Docker", "Kubernetes", "CI/CD", "System Design"],
            "headline_suggestion": f"{'Backend Engineer' if not target_role else target_role} | Python · FastAPI · PostgreSQL",
            "summary_suggestion": (
                "Results-driven engineer specializing in Python backend systems, "
                "REST APIs, and PostgreSQL. Passionate about building scalable, "
                "reliable distributed systems."
            ),
            "next_actions": [
                "Add 2 backend projects to demonstrate distributed systems skills",
                "Learn Docker and Kubernetes fundamentals",
                "Update profile headline to target your desired role",
            ],
            "experience_gaps": [
                "Production container orchestration",
                "Large-scale distributed systems",
                "CI/CD pipeline management",
            ],
        }

    async def generate_content(
        self,
        topic: str,
        context: dict[str, Any],
        content_type: str = "linkedin_post",
    ) -> dict[str, Any]:
        """Deterministic mock content generation."""
        return {
            "content": (
                f"🚀 Excited to share my latest work on {topic}!\n\n"
                "Building reliable backend systems has taught me that the best code "
                "is the code that fails gracefully. Here's what I learned:\n\n"
                "1. Start with clear contracts\n"
                "2. Test failure modes first\n"
                "3. Monitor everything\n\n"
                "What's your approach to building resilient systems?\n\n"
                "#SoftwareEngineering #Backend #TechCareers"
            ),
            "title": f"Lessons from {topic}",
            "hashtags": ["#SoftwareEngineering", "#Backend", "#TechCareers"],
            "confidence": 0.85,
            "sources_used": ["project experience", "career memory"],
        }

    async def generate_roadmap(
        self,
        profile_data: dict[str, Any],
        target_role: str,
        timeline_months: int = 6,
    ) -> dict[str, Any]:
        """Deterministic mock roadmap generation."""
        return {
            "target_role": target_role,
            "current_readiness": 72,
            "timeline_months": timeline_months,
            "milestones": [
                {
                    "title": "Docker & Container Fundamentals",
                    "description": "Learn Docker basics, create Dockerfiles, and manage multi-container apps",
                    "month": 1,
                    "category": "SKILL",
                    "priority": "HIGH",
                    "resources": ["Docker Official Docs", "Docker Deep Dive book"],
                },
                {
                    "title": "Build a Distributed Systems Project",
                    "description": "Create a microservices-based application with message queues",
                    "month": 3,
                    "category": "PROJECT",
                    "priority": "HIGH",
                    "resources": ["Designing Data-Intensive Applications", "GitHub"],
                },
                {
                    "title": "Kubernetes Basics",
                    "description": "Deploy applications to a Kubernetes cluster",
                    "month": 4,
                    "category": "SKILL",
                    "priority": "MEDIUM",
                    "resources": ["Kubernetes Up and Running", "KodeKloud"],
                },
                {
                    "title": "Start Applying to Target Roles",
                    "description": "Apply to 5-10 matching roles with tailored applications",
                    "month": 5,
                    "category": "APPLICATION",
                    "priority": "HIGH",
                    "resources": ["CareerOS Job Matching", "LinkedIn"],
                },
            ],
            "skill_gaps": [
                {"skill": "Docker", "current_level": "BEGINNER", "target_level": "ADVANCED", "priority": "HIGH"},
                {"skill": "Kubernetes", "current_level": "NONE", "target_level": "INTERMEDIATE", "priority": "HIGH"},
                {"skill": "CI/CD", "current_level": "BEGINNER", "target_level": "ADVANCED", "priority": "MEDIUM"},
                {"skill": "System Design", "current_level": "INTERMEDIATE", "target_level": "ADVANCED", "priority": "MEDIUM"},
            ],
        }


def get_ai_provider() -> AIProvider:
    """
    Return the configured AI Provider.
    Uses GeminiProvider when GEMINI_API_KEY is available, else falls back to MockAIProvider.
    """
    from apps.api.app.core.config import settings

    if settings.gemini_api_key and len(settings.gemini_api_key) > 10:
        try:
            from apps.api.app.services.ai.gemini_provider import GeminiProvider

            return GeminiProvider(api_key=settings.gemini_api_key)
        except Exception:
            pass

    return MockAIProvider()
