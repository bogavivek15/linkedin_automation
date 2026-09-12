from typing import Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException

from apps.api.app.core.security import AuthenticatedUser, get_current_user
from apps.api.app.domain.presence.models import PresencePost
from apps.api.app.services.presence.service import PresenceService

router = APIRouter(prefix="/presence", tags=["presence"])

@router.get("/posts", response_model=list[PresencePost])
async def list_posts(
    profile_id: str | None = None,
    status: str | None = None,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """List presence posts for the user."""
    service = PresenceService()
    return await service.list_posts(
        user_id=current_user.user_id,
        profile_id=profile_id,
        status=status,
    )

@router.post("/draft-from-memory", response_model=PresencePost)
async def generate_draft_from_memory(
    memory_id: str,
    profile_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Agent 4: Generate a new post draft from a memory, including image."""
    service = PresenceService()
    # This invokes the generator (Gemini) directly in our service layer
    try:
        return await service.draft_from_memory(
            memory_id=memory_id,
            user_id=current_user.user_id,
            profile_id=profile_id
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{post_id}/approve", response_model=PresencePost)
async def approve_post(
    post_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Approve a pending post (Human-in-the-Loop)."""
    service = PresenceService()
    try:
        return await service.approve_post(
            post_id=post_id,
            user_id=current_user.user_id
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{post_id}/regenerate-image", response_model=PresencePost)
async def regenerate_image(
    post_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Regenerate the image for a specific post."""
    service = PresenceService()
    post = await service.get_post(post_id, current_user.user_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
        
    from apps.api.app.domain.presence.generator import PresenceContentGenerator
    from apps.api.app.repositories.presence_repository import PresenceRepository
    
    new_image_uri = PresenceContentGenerator.generate_image_for_post(post)
    if new_image_uri:
        post.image_url = new_image_uri
        await PresenceRepository.save_post(post, current_user.user_id)
        
    return post
