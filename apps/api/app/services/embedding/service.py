import hashlib
from uuid import UUID

from apps.api.app.core.config import settings
from apps.api.app.domain.resume.models import EmbeddingRecord, ResumeChunk
from apps.api.app.services.embedding.provider import (
    EmbeddingProvider,
    get_embedding_provider,
)
from apps.api.app.services.embedding.validation import validate_vector


class EmbeddingService:
    """
    Core Domain Service for 768-dim semantic representations, content hashing,
    deduplication caching, and batch vector generation.
    """

    # In-memory deduplication cache: (content_hash, model_name, dimensions) -> vector
    _cache: dict[tuple[str, str, int], list[float]] = {}

    @classmethod
    def reset_cache(cls) -> None:
        """Helper for test isolation."""
        cls._cache.clear()

    @classmethod
    def compute_content_hash(cls, text: str) -> str:
        """
        Deterministic SHA-256 content hashing of canonical text.
        """
        canonical = text.strip()
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @classmethod
    def build_chunk_semantic_text(cls, section_type: str, content: str) -> str:
        """
        Format section-aware semantic text for embedding.
        """
        return f"Section: {section_type.upper()}\n{content.strip()}"

    @classmethod
    def build_project_semantic_text(
        cls,
        title: str,
        description: str,
        role: str | None = None,
        technologies: list[str] | None = None,
        outcomes: list[str] | None = None,
    ) -> str:
        """
        Format grounded project semantic text.
        """
        parts = [f"Project: {title.strip()}", f"Description: {description.strip()}"]
        if role:
            parts.append(f"Role: {role.strip()}")
        if technologies:
            parts.append(f"Technologies: {', '.join(technologies)}")
        if outcomes:
            parts.append(f"Outcomes: {'; '.join(outcomes)}")
        return "\n".join(parts)

    @classmethod
    def build_profile_semantic_text(
        cls,
        headline: str,
        summary: str,
        target_roles: list[str] | None = None,
        verified_skills: list[str] | None = None,
    ) -> str:
        """
        Format verified career profile semantic text.
        """
        parts = [f"Headline: {headline.strip()}", f"Summary: {summary.strip()}"]
        if target_roles:
            parts.append(f"Target Roles: {', '.join(target_roles)}")
        if verified_skills:
            parts.append(f"Verified Skills: {', '.join(verified_skills)}")
        return "\n".join(parts)

    @classmethod
    def build_job_semantic_text(
        cls,
        title: str,
        company: str,
        description: str,
        requirements: list[str] | None = None,
        skills: list[str] | None = None,
    ) -> str:
        """
        Format job semantic text (prepares interface for Phase 6).
        """
        parts = [
            f"Job Title: {title.strip()}",
            f"Company: {company.strip()}",
            f"Description: {description.strip()}",
        ]
        if requirements:
            parts.append(f"Requirements: {'; '.join(requirements)}")
        if skills:
            parts.append(f"Required Skills: {', '.join(skills)}")
        return "\n".join(parts)

    @classmethod
    async def embed_text(
        cls,
        text: str,
        provider: EmbeddingProvider | None = None,
    ) -> tuple[list[float], str]:
        """
        Embed a single text string with content-hash deduplication.
        Returns: (validated_768_float_vector, content_hash)
        """
        p = provider or get_embedding_provider()
        content_hash = cls.compute_content_hash(text)
        cache_key = (content_hash, p.model_name, p.dimensions)

        if cache_key in cls._cache:
            return cls._cache[cache_key], content_hash

        vector = await p.embed(text)
        validated = validate_vector(vector, p.dimensions)
        cls._cache[cache_key] = validated
        return validated, content_hash

    @classmethod
    async def embed_chunks(
        cls,
        chunks: list[ResumeChunk],
        provider: EmbeddingProvider | None = None,
    ) -> list[ResumeChunk]:
        """
        Batch-embed resume chunks with deduplication and bounded batching.
        Updates chunks with content_hash and embedding.
        """
        if not chunks:
            return []

        p = provider or get_embedding_provider()
        batch_size = settings.embedding_batch_size

        # 1. Prepare semantic texts and hashes
        semantic_texts: list[str] = []
        hashes: list[str] = []
        needed_texts: list[str] = []
        needed_indices: list[int] = []

        for idx, chunk in enumerate(chunks):
            sem_text = cls.build_chunk_semantic_text(chunk.section_type, chunk.content)
            h = cls.compute_content_hash(sem_text)
            chunk.content_hash = h
            semantic_texts.append(sem_text)
            hashes.append(h)

            cache_key = (h, p.model_name, p.dimensions)
            if cache_key in cls._cache:
                chunk.embedding = cls._cache[cache_key]
            else:
                needed_texts.append(sem_text)
                needed_indices.append(idx)

        # 2. Batch-embed missing chunks
        if needed_texts:
            for i in range(0, len(needed_texts), batch_size):
                batch_slice = needed_texts[i : i + batch_size]
                batch_vectors = await p.embed_batch(batch_slice)

                for j, vec in enumerate(batch_vectors):
                    chunk_idx = needed_indices[i + j]
                    validated_vec = validate_vector(vec, p.dimensions)
                    chunks[chunk_idx].embedding = validated_vec

                    cache_key = (hashes[chunk_idx], p.model_name, p.dimensions)
                    cls._cache[cache_key] = validated_vec

        return chunks

    @classmethod
    def create_embedding_record(
        cls,
        entity_type: str,
        entity_id: UUID,
        content_hash: str,
        embedding: list[float],
        user_id: UUID | None = None,
        source_type: str | None = None,
        source_id: UUID | None = None,
        provider: EmbeddingProvider | None = None,
    ) -> EmbeddingRecord:
        """
        Factory to construct traceable EmbeddingRecord metadata models.
        """
        p = provider or get_embedding_provider()
        return EmbeddingRecord(
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            source_type=source_type,
            source_id=source_id,
            model_name=p.model_name,
            model_version="v1",
            dimensions=p.dimensions,
            content_hash=content_hash,
            embedding=embedding,
        )
