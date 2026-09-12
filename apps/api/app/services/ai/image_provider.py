import os
import fal_client

from apps.api.app.core.config import settings

def generate_image(prompt: str, image_size: str = "landscape_4_3", model: str | None = None) -> str:
    """
    Generate an image using the FLUX model on fal.ai.
    Returns the URL of the generated image.
    """
    if settings.fal_key:
        os.environ["FAL_KEY"] = settings.fal_key

    target_model = model or settings.fal_image_model

    result = fal_client.subscribe(
        target_model,
        arguments={
            "prompt": prompt,
            "image_size": image_size,
            "num_inference_steps": 28,
            "guidance_scale": 3.5,
            "num_images": 1,
            "enable_safety_checker": True,
            "output_format": "jpeg"
        }
    )
    
    if "images" in result and len(result["images"]) > 0:
        return result["images"][0]["url"]
    
    raise RuntimeError(f"Image generation failed or returned no images: {result}")
