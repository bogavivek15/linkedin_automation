import logging
import base64
from typing import Optional
from apps.api.app.domain.gemini_client import get_gemini_client, genai_types
from apps.api.app.domain.presence.models import ContentType, PresencePost

logger = logging.getLogger("careeros.presence")

class PresenceContentGenerator:
    """Generates professional presence content using Google Gemini."""

    @staticmethod
    def draft_post_from_memory(
        user_id: str,
        profile_id: str,
        memory: dict,
        content_type: ContentType
    ) -> PresencePost:
        """
        Drafts a LinkedIn post based strictly on a memory (e.g. project, skill).
        """
        client = get_gemini_client()
        content_body = ""
        title = ""
        
        # Determine contextual titles and body snippets
        memory_title = memory.get('title', 'my latest career milestone')
        memory_content = memory.get('content', 'various engineering projects')
        
        # Robust fallback template when Gemini fails (Rate Limited or Unavailable)
        fallback_title = f"Career Update: {memory_title}"
        fallback_content = (
            f"Excited to share an update on my professional journey!\n\n"
            f"I've recently been focusing my efforts on deepening my skills and delivering impact. "
            f"Some highlights from my recent background include:\n\n"
            f"\"{memory_content}\"\n\n"
            f"I'm passionate about taking on complex engineering challenges and continuously learning. "
            f"Looking forward to exploring new opportunities and seeing what's next! 🚀\n\n"
            f"#CareerGrowth #Engineering #AlwaysLearning"
        )

        if not client:
            logger.warning("Gemini unavailable; using robust contextual fallback.")
            content_body = fallback_content
            title = fallback_title
        else:
            prompt = f"""
            Draft an engaging, professional LinkedIn post for a software engineering student.
            The post MUST be based strictly on this verified achievement/memory:
            {memory}
            
            Rules:
            1. Do not invent any metrics or skills not listed.
            2. Keep it humble but professional.
            3. Use line breaks and emojis where appropriate.
            4. Focus on the learning journey and technical details.
            
            Return ONLY the post text.
            """
            try:
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=genai_types.GenerateContentConfig(
                        temperature=0.4
                    )
                )
                content_body = response.text.strip()
                title = f"Milestone: {memory.get('title', 'Career Update')}"
            except Exception as e:
                logger.error(f"Failed to generate text from Gemini: {e}")
                # Use robust fallback instead of simple 1-line text
                content_body = fallback_content
                title = fallback_title
                
        return PresencePost(
            id=f"post-{user_id[:8]}-{memory.get('id', 'new')}",
            user_id=user_id,
            profile_id=profile_id,
            title=title,
            content_body=content_body,
            content_type=content_type,
            grounding_evidence_ids=[memory.get("id")] if memory.get("id") else []
        )

    @staticmethod
    def generate_image_for_post(post: PresencePost) -> Optional[str]:
        """
        Generates an image to accompany the post using Gemini Image Generation.
        Returns the image as a base64 string or URI.
        """
        client = get_gemini_client()
        if not client:
            logger.warning("Gemini unavailable; skipping image generation.")
            return None

        prompt = f"""
        A professional, sleek, and minimalist illustration to accompany a LinkedIn post about software engineering.
        The post is about: {post.title}.
        Do not include text in the image. Use a modern, tech-focused color palette.
        """
        try:
            # We use the Imagen 3 model for image generation
            result = client.models.generate_images(
                model='imagen-3.0-generate-001',
                prompt=prompt,
                config=genai_types.GenerateImagesConfig(
                    number_of_images=1,
                    output_mime_type="image/jpeg",
                    aspect_ratio="16:9"
                )
            )
            for generated_image in result.generated_images:
                # Convert the image bytes to a base64 data URI
                image_bytes = generated_image.image.image_bytes
                base64_encoded = base64.b64encode(image_bytes).decode('utf-8')
                return f"data:image/jpeg;base64,{base64_encoded}"
            return None
        except Exception as e:
            logger.error(f"Failed to generate image from Gemini: {e}")
            import random
            import urllib.parse
            # Context-aware fallback using pollinations.ai (free, no-key AI image generator)
            encoded_prompt = urllib.parse.quote(f"professional sleek tech illustration about {post.title} without text")
            seed = random.randint(1, 100000)
            return f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=600&height=400&nologo=true&seed={seed}"

    @staticmethod
    def generate_ideas(user_id: str, profile_id: str, memories: list[dict]) -> list[dict]:
        """Generate content ideas (used in the UI)."""
        return []
