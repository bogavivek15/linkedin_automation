"""
CareerOS Phase 8 — Semantic Similarity Service.

Computes cosine similarity between candidate profile and job using Phase 5 embeddings.
Falls back to 0 when embeddings are unavailable — never crashes the pipeline.
"""

from apps.api.app.core.logging import get_logger
from apps.api.app.services.embedding.provider import EmbeddingProvider, get_embedding_provider
from apps.api.app.services.embedding.search import cosine_similarity

logger = get_logger("careeros.matching.semantic")


async def calculate_semantic_score(
    candidate_text: str,
    job_text: str,
    candidate_embedding: list[float] | None = None,
    job_embedding: list[float] | None = None,
    provider: EmbeddingProvider | None = None,
) -> float:
    """
    Calculate semantic similarity between candidate profile and job.

    Uses precomputed embeddings when available, otherwise generates them on the fly.
    Returns a score normalized to 0-100.
    Falls back to 0.0 if computation fails (never crashes the matching pipeline).
    """
    try:
        emb_provider = provider or get_embedding_provider()

        # Use precomputed embeddings if available
        cand_vec = candidate_embedding
        job_vec = job_embedding

        # Generate candidate embedding if not precomputed
        if cand_vec is None and candidate_text and candidate_text.strip():
            cand_vec = await emb_provider.embed(candidate_text.strip())

        # Generate job embedding if not precomputed
        if job_vec is None and job_text and job_text.strip():
            job_vec = await emb_provider.embed(job_text.strip())

        # Compute cosine similarity
        if cand_vec and job_vec:
            raw_similarity = cosine_similarity(cand_vec, job_vec)
            # Normalize to 0-100 scale
            return round(raw_similarity * 100.0, 2)

        # One or both embeddings unavailable
        logger.warning("Semantic score fallback: one or both embeddings unavailable")
        return 0.0

    except Exception as e:
        logger.warning(f"Semantic score computation failed, falling back to 0: {e!s}")
        return 0.0


def build_candidate_text(
    career_summary: str = "",
    headline: str = "",
    skills: list[str] | None = None,
    experience_descriptions: list[str] | None = None,
) -> str:
    """
    Build a composite text representation of the candidate for embedding.
    """
    parts: list[str] = []

    if headline and headline.strip():
        parts.append(headline.strip())

    if career_summary and career_summary.strip():
        parts.append(career_summary.strip())

    if skills:
        skill_text = ", ".join(s for s in skills if s and s.strip())
        if skill_text:
            parts.append(f"Skills: {skill_text}")

    if experience_descriptions:
        for desc in experience_descriptions[:3]:
            if desc and desc.strip():
                parts.append(desc.strip())

    return " ".join(parts)


def build_job_text(
    title: str = "",
    description: str = "",
    required_skills: list[str] | None = None,
    preferred_skills: list[str] | None = None,
) -> str:
    """
    Build a composite text representation of the job for embedding.
    """
    parts: list[str] = []

    if title and title.strip():
        parts.append(title.strip())

    if description and description.strip():
        # Truncate very long descriptions for embedding quality
        parts.append(description.strip()[:2000])

    all_skills = (required_skills or []) + (preferred_skills or [])
    if all_skills:
        skill_text = ", ".join(s for s in all_skills if s and s.strip())
        if skill_text:
            parts.append(f"Skills: {skill_text}")

    return " ".join(parts)
