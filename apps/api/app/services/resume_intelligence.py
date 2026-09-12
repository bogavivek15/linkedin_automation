"""
CareerOS Phase 3 — Resume Intelligence & Provenance Bridging Service.

Transforms untrusted resume documents into structured Career Memory records:
Resume -> Parse -> Extract (profile, skills, projects, experience, education, certs, claims)
       -> Attach Provenance -> Store in Career Memory (AI_PROPOSED / EVIDENCE_VALIDATED)

Core Invariant:
"Resume says X" is distinct from "CareerOS verified X".
The resume is treated as evidence input, never absolute authoritative truth.
"""

import re
from typing import Any
from uuid import UUID

from apps.api.app.domain.memory.models import CareerMemoryRecord
from apps.api.app.domain.resume.models import ParsedResume
from apps.api.app.services.memory.service import MemoryService
from apps.api.app.services.resume_service import ResumeService
from pydantic import BaseModel, Field


class ResumeIntelligenceSummary(BaseModel):
    total_skills_extracted: int = 0
    total_projects_extracted: int = 0
    total_experience_extracted: int = 0
    total_education_extracted: int = 0
    total_certifications_extracted: int = 0
    total_claims_extracted: int = 0
    memories_recorded: int = 0


class ResumeIntelligenceResult(BaseModel):
    parsed_resume: ParsedResume
    extracted_memories: list[CareerMemoryRecord] = Field(default_factory=list)
    summary: ResumeIntelligenceSummary = Field(default_factory=ResumeIntelligenceSummary)


class ResumeIntelligenceService:
    """
    First-class service for extracting candidate intelligence from resumes
    and persisting it into Career Memory with strict provenance tagging.
    """

    def __init__(self, memory_service: MemoryService | None = None) -> None:
        self.memory_service = memory_service or MemoryService()

    async def ingest_resume(
        self,
        filename: str,
        content_type: str,
        file_bytes: bytes,
        user_id: UUID,
        profile_id: str | UUID | None = None,
    ) -> ResumeIntelligenceResult:
        """
        End-to-end resume intelligence workflow.
        """
        prof_id_str = str(profile_id or user_id)

        # 1. Defensive Parse and extract claims using existing ResumeService
        parsed = await ResumeService.parse_and_process_resume(
            filename=filename,
            content_type=content_type,
            file_bytes=file_bytes,
            user_id=user_id,
        )

        sections = parsed.sections or {}
        claims = parsed.claims or []
        recorded_memories: list[CareerMemoryRecord] = []
        resume_ref = str(parsed.id)

        # 2. Extract Profile / Summary
        summary_text = sections.get("SUMMARY", "").strip()
        if summary_text:
            mem = await self.memory_service.record_memory(
                user_id=user_id,
                profile_id=prof_id_str,
                category="PROFILE",
                key="resume_summary",
                content=summary_text,
                provenance=f"Resume: {parsed.file_name} (Section: Summary)",
                confidence=0.9,
                proposed_status="AI_PROPOSED",
                actor="AI_AGENT",
                evidence_provided=True,
                source="RESUME",
                evidence_ref=resume_ref,
                reason="Extracted candidate summary from resume",
                source_event="RESUME_INGESTED",
            )
            recorded_memories.append(mem)

        # 3. Extract Skills from SKILLS section and atomic claims
        skill_names: set[str] = set()
        skills_text = sections.get("SKILLS", "")
        if skills_text:
            # Tokenize skills by comma, bullet, newline, pipe
            tokens = re.split(r"[,;•|\n\r]+", skills_text)
            for t in tokens:
                cleaned = t.strip(" -:*#")
                if cleaned and len(cleaned) < 40 and not any(kw in cleaned.lower() for kw in ["skills", "proficient", "tools"]):
                    skill_names.add(cleaned)

        # Also pull from extracted atomic skill claims
        for claim in claims:
            if claim.claim_type == "SKILL":
                skill_names.add(claim.statement)

        for s_name in skill_names:
            norm_key = re.sub(r"[^a-z0-9_]", "_", s_name.lower().strip())
            mem = await self.memory_service.record_memory(
                user_id=user_id,
                profile_id=prof_id_str,
                category="SKILL",
                key=f"resume_skill:{norm_key}",
                content=f"Candidate resume mentions skill: {s_name}",
                provenance=f"Resume: {parsed.file_name} claim",
                confidence=0.85,
                proposed_status="AI_PROPOSED",
                actor="AI_AGENT",
                evidence_provided=True,
                source="RESUME",
                evidence_ref=resume_ref,
                reason="Stated on resume; unverified until confirmed by candidate or transcript evidence",
                source_event="RESUME_INGESTED",
            )
            recorded_memories.append(mem)

        # 4. Extract Projects
        projects_text = sections.get("PROJECTS", "")
        project_count = 0
        if projects_text:
            project_blocks = [b.strip() for b in re.split(r"\n\s*\n+", projects_text) if b.strip()]
            for idx, p_block in enumerate(project_blocks[:5]):
                first_line = p_block.splitlines()[0][:60]
                p_key = f"proj_{idx + 1}_{re.sub(r'[^a-z0-9]', '_', first_line.lower())[:30]}"
                mem = await self.memory_service.record_memory(
                    user_id=user_id,
                    profile_id=prof_id_str,
                    category="PROJECT",
                    key=f"resume_project:{p_key}",
                    content=p_block,
                    provenance=f"Resume: {parsed.file_name} (Section: Projects)",
                    confidence=0.9,
                    proposed_status="AI_PROPOSED",
                    actor="AI_AGENT",
                    evidence_provided=True,
                    source="RESUME",
                    evidence_ref=resume_ref,
                    reason="Extracted project milestone from resume",
                    source_event="RESUME_INGESTED",
                )
                recorded_memories.append(mem)
                project_count += 1

        # 5. Extract Experience
        exp_text = sections.get("EXPERIENCE", "")
        exp_count = 0
        if exp_text:
            exp_blocks = [b.strip() for b in re.split(r"\n\s*\n+", exp_text) if b.strip()]
            for idx, e_block in enumerate(exp_blocks[:5]):
                first_line = e_block.splitlines()[0][:60]
                e_key = f"exp_{idx + 1}_{re.sub(r'[^a-z0-9]', '_', first_line.lower())[:30]}"
                mem = await self.memory_service.record_memory(
                    user_id=user_id,
                    profile_id=prof_id_str,
                    category="EXPERIENCE",
                    key=f"resume_experience:{e_key}",
                    content=e_block,
                    provenance=f"Resume: {parsed.file_name} (Section: Experience)",
                    confidence=0.85,
                    proposed_status="AI_PROPOSED",
                    actor="AI_AGENT",
                    evidence_provided=True,
                    source="RESUME",
                    evidence_ref=resume_ref,
                    reason="Extracted employment history entry from resume",
                    source_event="RESUME_INGESTED",
                )
                recorded_memories.append(mem)
                exp_count += 1

        # 6. Extract Education
        edu_text = sections.get("EDUCATION", "")
        edu_count = 0
        if edu_text:
            edu_blocks = [b.strip() for b in re.split(r"\n\s*\n+", edu_text) if b.strip()]
            for idx, ed_block in enumerate(edu_blocks[:3]):
                ed_key = f"edu_{idx + 1}"
                mem = await self.memory_service.record_memory(
                    user_id=user_id,
                    profile_id=prof_id_str,
                    category="EDUCATION",
                    key=f"resume_education:{ed_key}",
                    content=ed_block,
                    provenance=f"Resume: {parsed.file_name} (Section: Education)",
                    confidence=0.9,
                    proposed_status="AI_PROPOSED",
                    actor="AI_AGENT",
                    evidence_provided=True,
                    source="RESUME",
                    evidence_ref=resume_ref,
                    reason="Extracted academic credential from resume",
                    source_event="RESUME_INGESTED",
                )
                recorded_memories.append(mem)
                edu_count += 1

        # 7. Extract Certifications
        cert_text = sections.get("CERTIFICATIONS", "")
        cert_count = 0
        if cert_text:
            cert_lines = [line.strip(" -•*") for line in cert_text.splitlines() if line.strip()]
            for idx, c_line in enumerate(cert_lines[:5]):
                c_key = f"cert_{idx + 1}_{re.sub(r'[^a-z0-9]', '_', c_line.lower())[:25]}"
                mem = await self.memory_service.record_memory(
                    user_id=user_id,
                    profile_id=prof_id_str,
                    category="CERTIFICATION",
                    key=f"resume_cert:{c_key}",
                    content=c_line,
                    provenance=f"Resume: {parsed.file_name} (Section: Certifications)",
                    confidence=0.9,
                    proposed_status="AI_PROPOSED",
                    actor="AI_AGENT",
                    evidence_provided=True,
                    source="RESUME",
                    evidence_ref=resume_ref,
                    reason="Extracted professional certificate from resume",
                    source_event="RESUME_INGESTED",
                )
                recorded_memories.append(mem)
                cert_count += 1

        summary = ResumeIntelligenceSummary(
            total_skills_extracted=len(skill_names),
            total_projects_extracted=project_count,
            total_experience_extracted=exp_count,
            total_education_extracted=edu_count,
            total_certifications_extracted=cert_count,
            total_claims_extracted=len(claims),
            memories_recorded=len(recorded_memories),
        )

        return ResumeIntelligenceResult(
            parsed_resume=parsed,
            extracted_memories=recorded_memories,
            summary=summary,
        )
