"""
CareerOS Phase 4 — Interview Intelligence Engine.

Generates strictly grounded interview preparation plans when an application reaches:
- ASSESSMENT
- INTERVIEW
- TECHNICAL
- HR

Invariant:
Never pretends to know confidential questions. Every recommendation is grounded in:
- job description & required skills
- candidate profile & verified facts
- resume claims & project evidence
- identified skill gaps
"""

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

InterviewStageType = Literal["ASSESSMENT", "INTERVIEW", "TECHNICAL", "HR"]


class GroundedTopicPrep(BaseModel):
    topic: str
    category: Literal["VERIFIED_STRENGTH", "SKILL_GAP_REVIEW", "PROJECT_EVIDENCE", "ROLE_MOTIVATION", "CORE_REQUIREMENT"]
    guidance: str
    evidence_citation: str | None = None


class InterviewPreparationPlan(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    lifecycle_id: str
    application_id: str
    user_id: str
    job_id: str
    company_name: str
    role_title: str
    stage: InterviewStageType
    overall_readiness: str = "HIGH"  # HIGH | MEDIUM | ATTENTION_NEEDED
    recommended_topics: list[GroundedTopicPrep] = Field(default_factory=list)
    key_project_evidence: list[str] = Field(default_factory=list)
    suggested_practice_questions: list[str] = Field(default_factory=list)
    talking_points: list[str] = Field(default_factory=list)
    warning_areas: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class InterviewIntelligenceEngine:
    """
    Synthesizes actionable, evidence-grounded preparation plans for candidate interviews.
    """

    @classmethod
    def generate_plan(
        cls,
        lifecycle_id: str,
        application_id: str,
        user_id: str,
        job_id: str,
        company_name: str,
        role_title: str,
        stage: InterviewStageType,
        job_requirements: list[str] | None = None,
        verified_skills: list[str] | None = None,
        missing_skills: list[str] | None = None,
        project_claims: list[dict[str, Any]] | None = None,
        resume_summary: str | None = None,
    ) -> InterviewPreparationPlan:
        """
        Generate grounded interview preparation strategy tailored to the specific stage.
        """
        reqs = job_requirements or []
        verified = verified_skills or []
        gaps = missing_skills or []
        projects = project_claims or []

        topics: list[GroundedTopicPrep] = []
        practice_questions: list[str] = []
        talking_points: list[str] = []
        warning_areas: list[str] = []
        key_projects: list[str] = []

        # 1. Project Evidence extraction
        for p in projects[:3]:
            title = p.get("title") or p.get("key") or "Technical Project"
            prov = p.get("provenance") or p.get("content") or "Verified artifact"
            key_projects.append(f"{title}: {prov}")
            topics.append(
                GroundedTopicPrep(
                    topic=title,
                    category="PROJECT_EVIDENCE",
                    guidance=f"Be ready to walk through architecture decisions and benchmarks in {title}.",
                    evidence_citation=prov,
                )
            )

        # 2. Stage-Specific Intelligence
        if stage == "ASSESSMENT":
            # Focus on test fundamentals and core requirements
            for r in reqs[:4]:
                topics.append(
                    GroundedTopicPrep(
                        topic=r,
                        category="CORE_REQUIREMENT",
                        guidance=f"Review fundamentals, common algorithmic patterns, and API signatures for {r}.",
                        evidence_citation=f"Required in {company_name} job posting",
                    )
                )
            practice_questions = [
                f"Implement core data structures and edge case handling using {verified[0] if verified else 'Python'}.",
                f"Analyze space-time complexity tradeoffs in asynchronous operations for {role_title}.",
                "Practice online code assessment questions covering standard error handling and testing.",
            ]
            talking_points = [
                f"Emphasize verified foundation in {', '.join(verified[:3])}.",
                "Focus on clean modular code with explicit type annotations and test coverage.",
            ]

        elif stage in ("INTERVIEW", "TECHNICAL"):
            # Focus on verified strengths + proactive answers for identified gaps
            for s in verified[:4]:
                topics.append(
                    GroundedTopicPrep(
                        topic=s,
                        category="VERIFIED_STRENGTH",
                        guidance=f"Highlight hands-on production or project implementation using {s}.",
                        evidence_citation="Candidate Verified Skill Profile",
                    )
                )

            for g in gaps[:3]:
                warning_areas.append(f"Potential skill gap: {g}")
                topics.append(
                    GroundedTopicPrep(
                        topic=g,
                        category="SKILL_GAP_REVIEW",
                        guidance=f"Acknowledge {g} as an adjacent growth area and connect it to your proven mastery in {verified[0] if verified else 'core systems'}.",
                        evidence_citation=f"Identified gap between profile and {role_title} requirements",
                    )
                )

            practice_questions = [
                f"How did you design and structure your backend systems in your recent projects?",
                f"Walk me through a production failure or race condition you debugged in {verified[0] if verified else 'Python'}.",
                f"How would you architect a scalable microservice handling real-time workflows for {company_name}?",
            ]
            talking_points = [
                f"Lead with concrete evidence from your verified projects ({', '.join(key_projects[:2]) if key_projects else 'GitHub repositories'}).",
                f"When discussing {', '.join(gaps[:2]) if gaps else 'unfamiliar tools'}, demonstrate rapid learning velocity by citing parallel frameworks you have mastered.",
            ]

        elif stage == "HR":
            # Focus on career trajectory, cultural fit, role motivation
            topics.append(
                GroundedTopicPrep(
                    topic="Role Motivation",
                    category="ROLE_MOTIVATION",
                    guidance=f"Articulate clear alignment between {company_name}'s mission and your career milestones.",
                    evidence_citation=f"Target role: {role_title}",
                )
            )
            topics.append(
                GroundedTopicPrep(
                    topic="Engineering Collaboration & Growth",
                    category="ROLE_MOTIVATION",
                    guidance="Share examples of code reviews, technical documentation, and cross-functional teamwork.",
                    evidence_citation="Candidate Work Experience",
                )
            )
            practice_questions = [
                f"What specifically drew you to apply for the {role_title} position at {company_name}?",
                "Tell me about a time you had to deliver a technical feature under tight deadlines or ambiguous requirements.",
                "Where do you envision your technical contribution focusing over the next 12 to 18 months?",
            ]
            talking_points = [
                f"State genuine enthusiasm for {company_name}'s technical product domain.",
                "Emphasize evidence-based problem solving and transparent communication.",
                "Discuss compensation expectations professionally aligned with published market ranges.",
            ]

        readiness = "HIGH" if len(gaps) <= 1 else ("MEDIUM" if len(gaps) <= 3 else "ATTENTION_NEEDED")

        return InterviewPreparationPlan(
            lifecycle_id=lifecycle_id,
            application_id=application_id,
            user_id=user_id,
            job_id=job_id,
            company_name=company_name,
            role_title=role_title,
            stage=stage,
            overall_readiness=readiness,
            recommended_topics=topics,
            key_project_evidence=key_projects,
            suggested_practice_questions=practice_questions,
            talking_points=talking_points,
            warning_areas=warning_areas,
        )
