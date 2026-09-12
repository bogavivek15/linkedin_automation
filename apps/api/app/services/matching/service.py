"""
CareerOS Phase 8 — Match Service (Main Orchestrator).

Pipeline:
    Load Profile → Load Job → Semantic → Skills → Experience → Location →
    Preferences → Constraints → Resume Selection → Score → Explanation → Persist

Core invariant: AI proposes. Evidence validates. Rules decide. Humans control exceptions.
"""

import time
from uuid import UUID

from apps.api.app.core.errors import CareerOSError
from apps.api.app.core.logging import get_logger
from apps.api.app.domain.job.models import CanonicalJob
from apps.api.app.domain.matching.constraint_engine import evaluate_constraints
from apps.api.app.domain.matching.experience_matcher import match_experience
from apps.api.app.domain.matching.explanation import (
    generate_explanation,
    generate_verification_questions,
)
from apps.api.app.domain.matching.location_matcher import match_location
from apps.api.app.domain.matching.models import (
    BatchMatchItem,
    BatchMatchResponse,
    CandidateProfile,
    MatchAgentOutput,
    MatchConfidence,
)
from apps.api.app.domain.matching.preference_matcher import match_preferences
from apps.api.app.domain.matching.resume_selector import (
    select_resume,
    suggest_resume_changes,
)
from apps.api.app.domain.matching.scoring import calculate_overall_score
from apps.api.app.domain.matching.skill_matcher import match_skills
from apps.api.app.repositories.job_repository import JobRepository
from apps.api.app.repositories.match_repository import MatchRepository
from apps.api.app.repositories.profile_repository import ProfileRepository
from apps.api.app.services.matching.semantic import (
    build_candidate_text,
    build_job_text,
    calculate_semantic_score,
)

logger = get_logger("careeros.matching.service")


class MatchService:
    """
    Main matching orchestrator — takes a verified student profile and a normalized job,
    and deterministically produces a structured, explainable ProfileMatch.
    """

    @classmethod
    async def calculate_match(
        cls,
        profile_id: UUID,
        job_id: UUID,
        user_id: UUID,
    ) -> MatchAgentOutput:
        """
        Calculate a single candidate-job match.

        Raises CareerOSError if profile or job is not found.
        """
        start_time = time.monotonic()
        logger.info(
            "MATCH_STARTED",
            extra={"profile_id": str(profile_id), "job_id": str(job_id)},
        )

        try:
            # 1. Load candidate profile
            candidate = await ProfileRepository.build_candidate_profile(
                profile_id=profile_id,
                user_id=user_id,
            )
            if not candidate:
                raise CareerOSError(
                    code="PROFILE_NOT_FOUND",
                    message=f"Career profile {profile_id} not found or inaccessible",
                    status_code=404,
                )

            # 2. Load job
            job = await JobRepository.get_job_by_id(job_id=job_id, user_id=user_id)
            if not job:
                raise CareerOSError(
                    code="JOB_NOT_FOUND",
                    message=f"Job {job_id} not found or inaccessible",
                    status_code=404,
                )

            # 3. Execute matching pipeline
            result = await cls._execute_pipeline(candidate, job)

            # 4. Persist match
            await MatchRepository.save_match(result, user_id=user_id)

            duration_ms = int((time.monotonic() - start_time) * 1000)
            logger.info(
                "MATCH_COMPLETED",
                extra={
                    "profile_id": str(profile_id),
                    "job_id": str(job_id),
                    "match_id": str(result.id),
                    "overall_score": result.overall_score,
                    "duration_ms": duration_ms,
                },
            )

            return result

        except CareerOSError:
            raise
        except Exception as e:
            logger.error(
                "MATCH_FAILED",
                extra={
                    "profile_id": str(profile_id),
                    "job_id": str(job_id),
                    "error": str(e),
                },
            )
            raise CareerOSError(
                code="MATCH_FAILED",
                message=f"Match calculation failed: {e!s}",
                status_code=500,
            )

    @classmethod
    async def calculate_batch(
        cls,
        profile_id: UUID,
        job_ids: list[UUID],
        user_id: UUID,
    ) -> BatchMatchResponse:
        """
        Calculate matches for multiple jobs. Graceful per-job failure.
        Bounded to max 20 jobs per batch.
        """
        if len(job_ids) > 20:
            raise CareerOSError(
                code="BATCH_TOO_LARGE",
                message="Batch size exceeds maximum of 20 jobs",
                status_code=400,
            )

        # Deduplicate job IDs
        unique_ids = list(dict.fromkeys(str(jid) for jid in job_ids))

        results: list[BatchMatchItem] = []
        succeeded = 0
        failed = 0

        for jid_str in unique_ids:
            jid = UUID(jid_str)
            try:
                match = await cls.calculate_match(profile_id, jid, user_id)
                results.append(BatchMatchItem(job_id=jid, match=match))
                succeeded += 1
            except Exception as e:
                results.append(BatchMatchItem(job_id=jid, error=str(e)))
                failed += 1

        return BatchMatchResponse(
            results=results,
            total_requested=len(unique_ids),
            total_succeeded=succeeded,
            total_failed=failed,
        )

    @classmethod
    async def _execute_pipeline(
        cls,
        candidate: CandidateProfile,
        job: CanonicalJob,
    ) -> MatchAgentOutput:
        """
        Core matching pipeline — all steps are deterministic.
        """
        # --- Semantic Similarity ---
        candidate_text = build_candidate_text(
            career_summary=candidate.career_summary,
            headline=candidate.headline,
            skills=[s.name for s in candidate.skills],
            experience_descriptions=[
                e.get("description", "") for e in candidate.experience_entries
            ],
        )
        job_text = build_job_text(
            title=job.title,
            description=job.description,
            required_skills=job.required_skills,
            preferred_skills=job.preferred_skills,
        )
        semantic_score = await calculate_semantic_score(
            candidate_text=candidate_text,
            job_text=job_text,
            candidate_embedding=candidate.embedding,
            job_embedding=job.embedding,
        )
        logger.info("SEMANTIC_MATCH_COMPLETED", extra={"score": semantic_score})

        # --- Skill Matching ---
        skill_result = match_skills(
            job_required=job.required_skills,
            job_preferred=job.preferred_skills,
            candidate_skills=candidate.skills,
        )
        logger.info("SKILL_MATCH_COMPLETED", extra={"score": skill_result.score})

        # --- Experience Matching ---
        experience_score, experience_label = match_experience(
            job_experience_min=job.experience_min,
            candidate_years=candidate.total_years_experience,
            job_employment_type=job.employment_type.value,
        )

        # --- Location Matching ---
        pref_locations = candidate.preferences.preferred_locations if candidate.preferences else []
        pref_modes = candidate.preferences.preferred_work_modes if candidate.preferences else []
        location_score, location_result = match_location(
            job_location=job.location,
            job_work_mode=job.work_mode.value,
            candidate_location=candidate.location,
            candidate_preferred_locations=pref_locations,
            candidate_preferred_work_modes=pref_modes,
        )

        # --- Preference Matching ---
        preference_score, preference_label = match_preferences(
            job_title=job.title,
            job_description=job.description,
            job_work_mode=job.work_mode.value,
            job_employment_type=job.employment_type.value,
            job_salary_min=job.salary_min,
            job_salary_max=job.salary_max,
            job_salary_currency=job.salary_currency,
            preferences=candidate.preferences,
        )

        # --- Hard Constraints ---
        constraint_result = evaluate_constraints(
            job_work_mode=job.work_mode.value,
            job_employment_type=job.employment_type.value,
            job_location=job.location,
            job_salary_min=job.salary_min,
            job_salary_max=job.salary_max,
            job_salary_currency=job.salary_currency,
            job_experience_min=job.experience_min,
            candidate_years_experience=candidate.total_years_experience,
            preferences=candidate.preferences,
        )
        logger.info(
            "CONSTRAINT_EVALUATED",
            extra={"passed": constraint_result.passed, "failures": len(constraint_result.failures)},
        )

        # --- Work Mode / Employment Type Match ---
        work_mode_match = "UNKNOWN"
        if candidate.preferences and candidate.preferences.preferred_work_modes:
            if job.work_mode.value in [m.upper() for m in candidate.preferences.preferred_work_modes]:
                work_mode_match = "MATCH"
            else:
                work_mode_match = "MISMATCH"

        employment_type_match = "UNKNOWN"
        if candidate.preferences and candidate.preferences.preferred_employment_types:
            if job.employment_type.value in [t.upper() for t in candidate.preferences.preferred_employment_types]:
                employment_type_match = "MATCH"
            else:
                employment_type_match = "MISMATCH"

        # --- Resume Selection ---
        resume_id, resume_reasons = select_resume(
            resume_ids=candidate.resume_ids,
            resume_skills=candidate.resume_skills,
            resume_texts=candidate.resume_texts,
            job_required_skills=job.required_skills,
            job_preferred_skills=job.preferred_skills,
            job_title=job.title,
            job_description=job.description,
        )
        if resume_id:
            logger.info("RESUME_SELECTED", extra={"resume_id": resume_id})

        # --- Resume Change Suggestions ---
        resume_changes = suggest_resume_changes(
            job_required_skills=job.required_skills,
            job_preferred_skills=job.preferred_skills,
            matched_skills=skill_result.matched,
            missing_skills=skill_result.missing,
            uncertain_skills=skill_result.uncertain,
        )

        # --- Verification Questions ---
        verification_questions = generate_verification_questions(
            missing_skills=skill_result.missing,
            uncertain_skills=skill_result.uncertain,
        )

        # --- Overall Score ---
        overall_score = calculate_overall_score(
            semantic_score=semantic_score,
            skill_score=skill_result.score,
            experience_score=experience_score,
            location_score=location_score,
            preference_score=preference_score,
        )

        # --- Confidence ---
        confidence = cls._assess_confidence(
            candidate=candidate,
            skill_result_uncertain_count=len(skill_result.uncertain),
            experience_label=experience_label,
            location_result=location_result.value,
        )

        # --- Build Output ---
        match_output = MatchAgentOutput(
            profile_id=candidate.profile_id,
            job_id=job.id,
            semantic_score=semantic_score,
            skill_score=skill_result.score,
            experience_score=experience_score,
            location_score=location_score,
            preference_score=preference_score,
            overall_score=overall_score,
            matched_skills=skill_result.matched,
            missing_skills=skill_result.missing,
            uncertain_skills=skill_result.uncertain,
            skill_match_details=skill_result.details,
            experience_match=experience_label,
            location_match=location_result.value,
            preference_match=preference_label,
            work_mode_match=work_mode_match,
            employment_type_match=employment_type_match,
            hard_constraints_passed=constraint_result.passed,
            hard_constraint_failures=constraint_result.failures,
            recommended_resume_id=resume_id,
            resume_changes=resume_changes,
            verification_questions=verification_questions,
            confidence=confidence,
        )

        # --- Explanation & Structured Breakdown ---
        from apps.api.app.domain.matching.explanation import generate_structured_breakdown

        explanation = generate_explanation(
            match=match_output,
            job_title=job.title,
            company_name=job.company_name,
        )
        match_output.explanation = explanation

        advantages = list(skill_result.matched)
        if location_result.value == "MATCH":
            advantages.append("Remote preference" if work_mode_match == "MATCH" else "Location match")
        potential_blockers = list(constraint_result.failures)
        if experience_label == "MISMATCH":
            potential_blockers.append(f"{job.experience_min or 2}+ years experience required")

        match_output.advantages = advantages
        match_output.potential_blockers = potential_blockers
        match_output.structured_breakdown = generate_structured_breakdown(match_output)

        return match_output

    @classmethod
    def _assess_confidence(
        cls,
        candidate: CandidateProfile,
        skill_result_uncertain_count: int,
        experience_label: str,
        location_result: str,
    ) -> MatchConfidence:
        """Determine overall confidence in the match result."""
        low_signals = 0

        if not candidate.skills:
            low_signals += 2
        if skill_result_uncertain_count > 2:
            low_signals += 1
        if experience_label == "UNKNOWN":
            low_signals += 1
        if location_result == "UNKNOWN":
            low_signals += 1
        if not candidate.preferences:
            low_signals += 1

        if low_signals >= 3:
            return MatchConfidence.LOW
        if low_signals >= 1:
            return MatchConfidence.MEDIUM
        return MatchConfidence.HIGH
