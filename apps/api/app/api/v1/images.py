from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Literal

from apps.api.app.services.ai.image_provider import generate_image
from apps.api.app.core.config import settings

router = APIRouter()

class ImageGenerationRequest(BaseModel):
    prompt: str
    image_size: Literal[
        "square_hd", "square", "portrait_4_3", "portrait_16_9", "landscape_4_3", "landscape_16_9"
    ] = "landscape_4_3"
    model: str | None = None

class ImageGenerationResponse(BaseModel):
    url: str

@router.post("/generate", response_model=ImageGenerationResponse)
async def generate_image_endpoint(request: ImageGenerationRequest):
    """
    Generate an image via fal.ai.
    """
    if not settings.fal_key:
        raise HTTPException(status_code=500, detail="FAL_KEY is not configured on the server.")
        
    try:
        url = generate_image(prompt=request.prompt, image_size=request.image_size, model=request.model)
        return ImageGenerationResponse(url=url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
