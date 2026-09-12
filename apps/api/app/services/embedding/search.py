import math

from apps.api.app.core.security import AuthenticatedUser
from apps.api.app.domain.resume.models import SemanticSearchResult
from apps.api.app.repositories.resume_repository import ResumeRepository
from apps.api.app.services.embedding.provider import (
    EmbeddingProvider,
)
from apps.api.app.services.embedding.service import EmbeddingService


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """
    Compute cosine similarity between two numeric vectors.
    Returns normalized float between 0.0 and 1.0.
    """
    if len(vec_a) != len(vec_b) or not vec_a:
        return 0.0

    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    raw_cos = dot / (norm_a * norm_b)
    # Clamp to [0.0, 1.0] for application score consistency
    clamped = max(0.0, min(1.0, (raw_cos + 1.0) / 2.0 if raw_cos < 0 else raw_cos))
    return round(clamped, 4)


class SemanticSearchService:
    """
    Performs vector similarity search strictly scoped to the authenticated user.
    """

    @classmethod
    async def search(
        cls,
        query: str,
        current_user: AuthenticatedUser,
        *,
        entity_type: str | None = None,
        limit: int = 10,
        min_similarity: float = 0.0,
        provider: EmbeddingProvider | None = None,
    ) -> list[SemanticSearchResult]:
        """
        1. Embed user query using 768-dim embedding provider.
        2. Retrieve user-owned candidate vectors from repository.
        3. Compute cosine similarity.
        4. Filter and rank results.
        """
        if not query or not query.strip():
            return []

        # Generate query vector
        query_vector, _ = await EmbeddingService.embed_text(query, provider=provider)

        # Retrieve vectors strictly belonging to current user
        candidates = await ResumeRepository.get_user_chunks_with_embeddings(
            user_id=current_user.user_id,
            entity_type=entity_type,
        )

        results: list[SemanticSearchResult] = []

        for item in candidates:
            chunk_vec = item.get("embedding")
            if not chunk_vec:
                continue

            sim = cosine_similarity(query_vector, chunk_vec)
            if sim >= min_similarity:
                results.append(
                    SemanticSearchResult(
                        entity_id=item["id"],
                        entity_type=item.get("entity_type", "RESUME_CHUNK"),
                        similarity=sim,
                        content=item.get("content", ""),
                        section_type=item.get("section_type"),
                        source_type=item.get("source_type", "RESUME"),
                        source_id=item.get("resume_id"),
                        metadata={
                            "chunk_index": item.get("chunk_index"),
                            "content_hash": item.get("content_hash"),
                            "file_name": item.get("file_name"),
                        },
                    )
                )

        # Sort descending by cosine similarity
        results.sort(key=lambda r: r.similarity, reverse=True)
        return results[:limit]
