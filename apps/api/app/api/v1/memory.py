"""
CareerOS Phase 14 — Career Memory & Persistent Knowledge System API.

Endpoints:
POST   /api/v1/memory                        - Record or propose memory item
GET    /api/v1/memory                        - List memories with filters
GET    /api/v1/memory/retrieve/application   - Contextual retrieval for application
GET    /api/v1/memory/retrieve/presence      - Contextual retrieval for presence
GET    /api/v1/memory/{memory_id}            - Get specific memory item
POST   /api/v1/memory/{memory_id}/confirm    - User confirms memory item
DELETE /api/v1/memory/{memory_id}            - Delete memory item
"""

from typing import Any
from uuid import UUID

from apps.api.app.core.errors import CareerOSError
from apps.api.app.core.security import AuthenticatedUser, get_current_user
from apps.api.app.domain.memory.models import (
    MemoryCategory,
    MemoryVerificationStatus,
)
from apps.api.app.services.memory.service import MemoryService
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/memory", tags=["Career Memory"])

_service = MemoryService()


class RecordMemoryRequest(BaseModel):
    profile_id: UUID
    category: MemoryCategory
    key: str
    content: str
    provenance: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    proposed_status: MemoryVerificationStatus = "AI_PROPOSED"
    actor: str = "USER"  # Defaulting client calls to USER unless specified
    evidence_provided: bool = False
    source_event: str | None = None
    source_ref_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConfirmSkillRequest(BaseModel):
    profile_id: UUID
    skill_name: str
    confirmed: bool = True
    evidence: str | None = None
    years_experience: float = 1.0
    proficiency: str = "INTERMEDIATE"
    recalculate_job_ids: list[UUID] = Field(default_factory=list)


@router.post("/confirm-skill", response_model=dict)
async def confirm_skill(
    request: ConfirmSkillRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Candidate confirms or declines a skill.
    If confirmed:
      - Records verified skill in persistent career memory
      - Updates candidate profile skills
      - Recalculates affected job matches
    If declined:
      - Records skill gap with recommended learning
    """
    from apps.api.app.domain.matching.models import ProfileSkillRecord
    from apps.api.app.repositories.profile_repository import ProfileRepository
    from apps.api.app.services.matching.service import MatchService

    skill_norm = request.skill_name.strip().lower()

    if request.confirmed:
        evidence_text = request.evidence or "Student confirmed knowledge with evidence"
        mem = await _service.record_memory(
            user_id=current_user.user_id,
            profile_id=str(request.profile_id),
            category="SKILL",
            key=f"skill:{skill_norm}",
            content=f"Verified skill: {request.skill_name}. Evidence: {evidence_text}",
            provenance=f"USER_CONFIRMED: {evidence_text}",
            confidence=1.0,
            proposed_status="USER_CONFIRMED",
            actor="USER",
            evidence_provided=True,
            source_event="SKILL_CONFIRMED",
        )

        skill_record = ProfileSkillRecord(
            profile_id=request.profile_id,
            user_id=current_user.user_id,
            skill_name=request.skill_name,
            normalized_name=skill_norm,
            proficiency=request.proficiency,
            years_experience=request.years_experience,
            verified_status="STUDENT_CONFIRMED",
            source="STUDENT_CONFIRMED",
        )
        await ProfileRepository.save_profile_skill(skill_record)

        recalculated_matches = []
        for jid in request.recalculate_job_ids:
            try:
                m = await MatchService.calculate_match(
                    profile_id=request.profile_id,
                    job_id=jid,
                    user_id=current_user.user_id,
                )
                recalculated_matches.append(m.model_dump(mode="json"))
            except Exception:
                pass

        return {
            "success": True,
            "data": {
                "skill": request.skill_name,
                "status": "CONFIRMED",
                "memory": mem.model_dump(mode="json"),
                "recalculated_matches": recalculated_matches,
            },
        }
    else:
        mem = await _service.record_memory(
            user_id=current_user.user_id,
            profile_id=str(request.profile_id),
            category="FEEDBACK",
            key=f"skill_gap:{skill_norm}",
            content=f"Student confirmed no experience with {request.skill_name}. Recommended for learning.",
            provenance="USER_CONFIRMED_GAP",
            confidence=1.0,
            proposed_status="USER_CONFIRMED",
            actor="USER",
            evidence_provided=False,
            source_event="SKILL_GAP_CONFIRMED",
        )
        return {
            "success": True,
            "data": {
                "skill": request.skill_name,
                "status": "GAP_RECORDED",
                "recommendation": f"Explore tutorials and coursework for {request.skill_name} to qualify for targeted opportunities.",
                "memory": mem.model_dump(mode="json"),
            },
        }


@router.post("", response_model=dict)
async def record_memory(
    request: RecordMemoryRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Record or propose a memory item. Enforces deterministic memory safety policy.
    """
    try:
        record = await _service.record_memory(
            user_id=current_user.user_id,
            profile_id=str(request.profile_id),
            category=request.category,
            key=request.key,
            content=request.content,
            provenance=request.provenance,
            confidence=request.confidence,
            proposed_status=request.proposed_status,
            actor=request.actor,
            evidence_provided=request.evidence_provided,
            source_event=request.source_event,
            source_ref_id=request.source_ref_id,
            metadata=request.metadata,
        )
        return {"success": True, "data": record.model_dump(mode="json")}
    except CareerOSError as e:
        raise HTTPException(status_code=e.status_code, detail={"code": e.code, "message": e.message})


@router.get("", response_model=dict)
async def list_memories(
    category: MemoryCategory | None = Query(default=None),
    profile_id: str | None = Query(default=None),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    List career memories for the authenticated user.
    """
    memories = await _service.list_memories(
        user_id=current_user.user_id,
        category=category,
        profile_id=profile_id,
    )
    return {"success": True, "data": [m.model_dump(mode="json") for m in memories]}


@router.get("/retrieve/application", response_model=dict)
async def retrieve_for_application(
    profile_id: str | None = Query(default=None),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Retrieve evidence-grounded memories organized for application tailoring.
    """
    grouped = await _service.retrieve_for_application(
        user_id=current_user.user_id,
        profile_id=profile_id,
    )
    return {
        "success": True,
        "data": {
            cat: [m.model_dump(mode="json") for m in items]
            for cat, items in grouped.items()
        },
    }


@router.get("/retrieve/presence", response_model=dict)
async def retrieve_for_presence(
    profile_id: str | None = Query(default=None),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Retrieve verified memories for professional presence content generation.
    """
    memories = await _service.retrieve_for_presence(
        user_id=current_user.user_id,
        profile_id=profile_id,
    )
    return {"success": True, "data": [m.model_dump(mode="json") for m in memories]}


@router.get("/{memory_id}", response_model=dict)
async def get_memory(
    memory_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Retrieve a specific memory item.
    """
    memory = await _service.get_memory(memory_id, current_user.user_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory item not found")
    return {"success": True, "data": memory.model_dump(mode="json")}


@router.post("/{memory_id}/confirm", response_model=dict)
async def confirm_memory(
    memory_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Allow candidate user to confirm an AI-proposed or evidence-validated memory item.
    """
    updated = await _service.confirm_memory(memory_id, current_user.user_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Memory item not found")
    return {"success": True, "data": updated.model_dump(mode="json")}


@router.delete("/{memory_id}", response_model=dict)
async def delete_memory(
    memory_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Delete a memory item.
    """
    deleted = await _service.delete_memory(memory_id, current_user.user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory item not found")
    return {"success": True, "data": {"deleted": True}}


@router.get("/timeline", response_model=dict)
async def get_memory_timeline(
    profile_id: str | None = Query(default=None),
    limit: int = Query(default=30, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Retrieve human-readable, chronological audit timeline of Career Memory records and milestones.
    """
    from apps.api.app.services.memory.timeline import CareerMemoryTimelineService
    timeline_service = CareerMemoryTimelineService()
    entries = await timeline_service.get_timeline(
        user_id=current_user.user_id,
        profile_id=profile_id,
        limit=limit,
    )
    return {
        "success": True,
        "total_entries": len(entries),
        "data": [e.model_dump(mode="json") for e in entries],
    }

