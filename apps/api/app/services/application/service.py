"""
CareerOS Phase 10 — Application Preparation Service.

Orchestrates complete, evidence-grounded application package preparation:
1. Decision policy gating (Phase 9 integration)
2. Context & evidence loading (Phase 4-8)
3. Requirement extraction & prompt injection quarantine
4. Evidence-backed resume tailoring with explicit diffs
5. Grounded cover letter generation
6. Question answering with automatic sensitivity & verification flags
7. Deterministic claim & metric safety validation
8. Multi-dimensional quality scoring
9. Versioned package assembly and persistence

Strict Boundary:
No live submission, browser automation, credential storage, or CAPTCHA bypass.
"""

from typing import Any
from uuid import UUID, uuid4

from apps.api.app.core.errors import CareerOSError
from apps.api.app.domain.application.claims import VerifiedClaimIndex
from apps.api.app.domain.application.models import (
    ApplicationAnswer,
    ApplicationPackage,
)
from apps.api.app.domain.application.package import assemble_application_package
from apps.api.app.domain.application.quality import evaluate_application_quality
from apps.api.app.domain.application.requirements import extract_job_requirements
from apps.api.app.domain.application.validator import validate_application_package
from apps.api.app.repositories.application_repository import ApplicationRepository
from apps.api.app.repositories.decision_repository import DecisionRepository
from apps.api.app.repositories.job_repository import JobRepository
from apps.api.app.repositories.profile_repository import ProfileRepository
from apps.api.app.repositories.resume_repository import ResumeRepository
from apps.api.app.repositories.tailored_resume_repository import (
    TailoredResumeRepository,
)
from apps.api.app.services.application.provider import (
    ApplicationGenerationProvider,
    MockApplicationProvider,
)


class ApplicationPreparationService:
    """
    Core service for preparing verifiable, job-specific application packages.
    """

    def __init__(
        self,
        provider: ApplicationGenerationProvider | None = None,
    ) -> None:
        self.provider = provider or MockApplicationProvider()

    async def prepare_application(
        self,
        profile_id: str | UUID,
        job_id: str | UUID,
        user_id: UUID,
        base_resume_id: str | UUID | None = None,
        instructions: str | None = None,
        package_version: str = "v1",
    ) -> ApplicationPackage:
        """
        Prepare a complete application package for an opportunity.
        """
        prof_uuid = UUID(str(profile_id))
        job_uuid = UUID(str(job_id))

        # 1. Load Opportunity Decision to verify preparation eligibility
        decision = await DecisionRepository.get_decision_for_job(
            profile_id=prof_uuid,
            job_id=job_uuid,
            user_id=user_id,
        )
        decision_id = str(decision.id) if decision else None
        decision_action = decision.action if decision else None

        # If decision is REJECT, block immediately
        if decision_action == "REJECT":
            blocked_pkg = ApplicationPackage(
                profile_id=str(profile_id),
                job_id=str(job_id),
                decision_id=decision_id,
                validation_status="BLOCKED",
                quality_status="FAILED",
                blocking_issues=["Application preparation blocked: Opportunity marked REJECT by decision policy."],
                package_version=package_version,
            )
            return await ApplicationRepository.save_package(blocked_pkg, user_id)

        # 2. Load Job Record
        job = await JobRepository.get_job_by_id(job_uuid, user_id)
        if not job:
            raise CareerOSError(
                code="JOB_NOT_FOUND",
                message=f"Job with ID '{job_id}' not found",
                status_code=404,
            )
        job_dict = job.model_dump(mode="json") if hasattr(job, "model_dump") else dict(job)

        # 3. Load Candidate Profile & Preferences
        profile_dict = await ProfileRepository.get_profile(prof_uuid, user_id)
        if not profile_dict:
            raise CareerOSError(
                code="PROFILE_NOT_FOUND",
                message=f"Profile with ID '{profile_id}' not found",
                status_code=404,
            )
        prefs = await ProfileRepository.get_preferences(prof_uuid, user_id)
        prefs_dict = prefs.model_dump(mode="json") if prefs else {}

        # 4. Load Verified Claims
        verified_claims = await self._load_verified_claim_index(
            profile_id=prof_uuid,
            user_id=user_id,
            base_resume_id=base_resume_id,
        )

        # 5. Select Base Resume
        selected_resume = await self._select_base_resume(
            user_id=user_id,
            base_resume_id=base_resume_id,
            profile_dict=profile_dict,
        )
        actual_resume_id = str(selected_resume.get("id"))

        # 6. Extract Job Requirements
        job_requirements = extract_job_requirements(job_dict)

        # 7. Tailor Resume
        tailored_resume = await self.provider.tailor_resume(
            base_resume=selected_resume,
            job_requirements=job_requirements,
            verified_claims=verified_claims,
            job_id=str(job_id),
            profile_id=str(profile_id),
            instructions=instructions,
        )

        # 8. Generate Cover Letter
        cover_letter_text, cl_cids = await self.provider.generate_cover_letter(
            profile_data=profile_dict,
            job_data=job_dict,
            job_requirements=job_requirements,
            verified_claims=verified_claims,
            instructions=instructions,
        )

        # 9. Extract and Answer Application Questions
        questions_to_ask = [
            req.text
            for req in job_requirements
            if req.category == "APPLICATION_QUESTION"
        ]
        # Always include role motivation question if not already asked
        if not any("why" in q.lower() or "interest" in q.lower() for q in questions_to_ask):
            questions_to_ask.insert(0, "Why are you interested in this role?")

        answers: list[ApplicationAnswer] = []
        for q in questions_to_ask:
            ans = await self.provider.generate_answer(
                question=q,
                profile_data=profile_dict,
                job_data=job_dict,
                verified_claims=verified_claims,
                preferences=prefs_dict,
                instructions=instructions,
            )
            answers.append(ans)

        # 10. Identify Selected Skills & Supporting Claims
        selected_skills = [
            r.normalized_value or r.text
            for r in job_requirements
            if r.category == "SKILL" and verified_claims.is_skill_verified(r.normalized_value or r.text)
        ]
        all_supporting_claim_ids = set(tailored_resume.supporting_claim_ids + cl_cids)
        for ans in answers:
            all_supporting_claim_ids.update(ans.supporting_claim_ids)

        # 11. Deterministic Claim Validation
        draft_pkg = ApplicationPackage(
            profile_id=str(profile_id),
            job_id=str(job_id),
            decision_id=decision_id,
            resume_id=actual_resume_id,
            tailored_resume_id=tailored_resume.id,
            tailored_resume=tailored_resume,
            cover_letter=cover_letter_text,
            application_answers=answers,
            selected_skills=selected_skills,
            supporting_claim_ids=list(all_supporting_claim_ids),
            package_version=package_version,
        )
        validation_result = validate_application_package(draft_pkg, verified_claims)

        # 12. Quality Scoring & Requirement Coverage
        quality = evaluate_application_quality(
            package=draft_pkg,
            job_requirements=job_requirements,
            verified_claims=verified_claims,
            validation_result=validation_result,
        )

        # 13. Assemble Application Package
        package = assemble_application_package(
            profile_id=str(profile_id),
            job_id=str(job_id),
            decision_id=decision_id,
            decision_action=decision_action,
            resume_id=actual_resume_id,
            tailored_resume=tailored_resume,
            cover_letter=cover_letter_text,
            answers=answers,
            selected_skills=selected_skills,
            supporting_claim_ids=list(all_supporting_claim_ids),
            validation_result=validation_result,
            quality=quality,
            package_version=package_version,
        )

        # 14. Persist Artifacts
        await TailoredResumeRepository.save_tailored_resume(tailored_resume, user_id)
        saved_pkg = await ApplicationRepository.save_package(package, user_id)
        return saved_pkg

    async def get_package(
        self,
        package_id: str | UUID,
        user_id: UUID,
    ) -> ApplicationPackage | None:
        """Retrieve package enforcing user isolation."""
        return await ApplicationRepository.get_package(package_id, user_id)

    async def get_package_for_job(
        self,
        job_id: str | UUID,
        user_id: UUID,
    ) -> ApplicationPackage | None:
        """Retrieve latest package for job."""
        return await ApplicationRepository.get_package_for_job(job_id, user_id)

    async def list_packages(
        self,
        user_id: UUID,
        status: str | None = None,
    ) -> list[ApplicationPackage]:
        """List application packages for a user."""
        return await ApplicationRepository.list_packages_for_user(user_id, status)

    async def approve_package(
        self,
        package_id: str | UUID,
        user_id: UUID,
    ) -> ApplicationPackage:
        """
        User approval transition: READY_FOR_REVIEW -> APPROVED.
        Strictly does NOT submit the application.
        """
        pkg = await ApplicationRepository.get_package(package_id, user_id)
        if not pkg:
            raise CareerOSError(
                code="PACKAGE_NOT_FOUND",
                message=f"Application package '{package_id}' not found",
                status_code=404,
            )

        if pkg.validation_status == "BLOCKED":
            raise CareerOSError(
                code="PACKAGE_BLOCKED",
                message="Cannot approve a blocked application package. Resolve blocking issues first.",
                status_code=400,
            )

        updated = await ApplicationRepository.update_package_status(package_id, user_id, "APPROVED")
        if not updated:
            raise CareerOSError(code="UPDATE_FAILED", message="Failed to update package status", status_code=500)
        return updated

    async def regenerate_package(
        self,
        package_id: str | UUID,
        user_id: UUID,
        instructions: str | None = None,
    ) -> ApplicationPackage:
        """
        Regenerate an application package with student instructions, creating a new controlled version.
        """
        existing = await ApplicationRepository.get_package(package_id, user_id)
        if not existing:
            raise CareerOSError(
                code="PACKAGE_NOT_FOUND",
                message=f"Application package '{package_id}' not found",
                status_code=404,
            )

        current_ver = existing.package_version
        # Increment version: "v1" -> "v2"
        try:
            ver_num = int(current_ver.replace("v", ""))
            new_version = f"v{ver_num + 1}"
        except ValueError:
            new_version = f"{current_ver}_next"

        return await self.prepare_application(
            profile_id=existing.profile_id,
            job_id=existing.job_id,
            user_id=user_id,
            base_resume_id=existing.resume_id,
            instructions=instructions,
            package_version=new_version,
        )

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    async def _load_verified_claim_index(
        self,
        profile_id: UUID,
        user_id: UUID,
        base_resume_id: str | UUID | None,
    ) -> VerifiedClaimIndex:
        """Assemble all verified candidate claims into the index."""
        index = VerifiedClaimIndex()

        # 1. Claims from ResumeRepository
        if base_resume_id:
            claims_data = ResumeRepository._claims.get(str(base_resume_id), [])
            for c in claims_data:
                index.add_claim(c)

        # Also load all user resume claims
        for r_id, claims_list in ResumeRepository._claims.items():
            r_doc = ResumeRepository._resumes.get(r_id)
            if r_doc and r_doc.get("user_id") == user_id:
                for c in claims_list:
                    index.add_claim(c)

        # 2. Skills from ProfileRepository
        profile_skills = await ProfileRepository.get_profile_skills(profile_id, user_id)
        for ps in profile_skills:
            if ps.verified_status.upper() in ("VERIFIED", "STUDENT_CONFIRMED"):
                index.add_claim(
                    {
                        "id": str(ps.id),
                        "claim_type": "SKILL",
                        "statement": ps.skill_name,
                        "source_type": ps.source,
                        "evidence_text": f"Profile verified skill: {ps.skill_name} ({ps.proficiency})",
                        "verification_status": "VERIFIED",
                        "allowed_in_tailoring": True,
                        "confidence_score": 1.0,
                    }
                )

        # 3. Experience & Projects from Profile
        profile_doc = await ProfileRepository.get_profile(profile_id, user_id)
        if profile_doc:
            for exp in profile_doc.get("experience", []):
                role = exp.get("role", "")
                company = exp.get("company", "")
                desc = exp.get("description", "")
                exp_id = str(exp.get("id", uuid4()))
                index.add_claim(
                    {
                        "id": exp_id,
                        "claim_type": "RESPONSIBILITY",
                        "statement": f"{role} at {company}",
                        "source_type": "EXPERIENCE",
                        "evidence_text": f"{role} at {company}: {desc}",
                        "verification_status": "VERIFIED",
                        "allowed_in_tailoring": True,
                        "confidence_score": 1.0,
                    }
                )
            for proj in profile_doc.get("projects", []):
                name = proj.get("name", "")
                desc = proj.get("description", "")
                proj_id = str(proj.get("id", uuid4()))
                index.add_claim(
                    {
                        "id": proj_id,
                        "claim_type": "OUTCOME",
                        "statement": f"Built {name}",
                        "source_type": "PROJECT",
                        "evidence_text": f"{name}: {desc}",
                        "verification_status": "VERIFIED",
                        "allowed_in_tailoring": True,
                        "confidence_score": 1.0,
                    }
                )

        return index

    async def _select_base_resume(
        self,
        user_id: UUID,
        base_resume_id: str | UUID | None,
        profile_dict: dict[str, Any],
    ) -> dict[str, Any]:
        """Select or construct the base resume for tailoring."""
        if base_resume_id:
            r_doc = ResumeRepository._resumes.get(str(base_resume_id))
            if r_doc and r_doc.get("user_id") == user_id:
                return r_doc

        # Find best existing resume for user
        user_resumes = [
            r for r in ResumeRepository._resumes.values()
            if r.get("user_id") == user_id
        ]
        if user_resumes:
            # Pick master or first
            master = next((r for r in user_resumes if r.get("is_master")), user_resumes[0])
            return master

        # Synthesize base resume from profile if none uploaded
        synth_id = str(uuid4())
        summary = profile_dict.get("career_summary") or profile_dict.get("headline") or "Software Engineer"
        synth_doc = {
            "id": synth_id,
            "user_id": user_id,
            "profile_id": profile_dict.get("id"),
            "file_name": "Profile_Generated_Resume.pdf",
            "raw_text": f"SUMMARY\n{summary}\n",
            "sections": {
                "SUMMARY": summary,
                "SKILLS": "",
                "EXPERIENCE": "",
                "PROJECTS": "",
                "EDUCATION": "",
            },
            "is_master": True,
        }
        ResumeRepository._resumes[synth_id] = synth_doc
        return synth_doc
