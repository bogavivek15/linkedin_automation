from datetime import datetime, timezone
from uuid import UUID

from apps.api.app.core.config import settings
from apps.api.app.core.errors import CareerOSError
from apps.api.app.core.security import AuthenticatedUser
from apps.api.app.domain.resume.models import (
    ParsedResume,
    ResumeClaim,
)


class ResumeRepository:
    """
    Repository for Resumes, Chunks, Claims, and Vector Embeddings.
    Adheres strictly to supabase migrations:
    - 004_resumes.sql
    - 013_rls.sql (user_id isolation)
    - 015_embeddings.sql (vector metadata & deduplication)
    Provides in-memory transactional store for zero-dependency test/demo execution.
    """

    # In-memory store keyed by UUID string
    _resumes: dict[str, dict] = {}
    _chunks: dict[str, list[dict]] = {}
    _claims: dict[str, list[dict]] = {}
    _embedding_records: dict[str, dict] = {}  # key: content_hash:model_name:dimensions

    @classmethod
    def reset_store(cls) -> None:
        """Helper for test isolation."""
        cls._resumes.clear()
        cls._chunks.clear()
        cls._claims.clear()
        cls._embedding_records.clear()

    @classmethod
    async def save_parsed_resume(
        cls,
        parsed_resume: ParsedResume,
        user: AuthenticatedUser,
        profile_id: UUID | None = None,
    ) -> ParsedResume:
        """
        Persist Resume record, Chunks with embeddings, and Claims transactionally.
        """
        user_id = user.user_id
        resume_id_str = str(parsed_resume.id)
        now = datetime.now(timezone.utc).isoformat()

        # In-memory / Demo store
        cls._resumes[resume_id_str] = {
            "id": parsed_resume.id,
            "user_id": user_id,
            "profile_id": profile_id or user_id,
            "title": parsed_resume.file_name,
            "file_name": parsed_resume.file_name,
            "file_path": f"/resumes/{parsed_resume.file_name}",
            "file_size": parsed_resume.file_size,
            "mime_type": parsed_resume.mime_type,
            "raw_text": parsed_resume.raw_text,
            "sections": parsed_resume.sections or {},
            "status": parsed_resume.status,
            "is_master": True,
            "created_at": now,
            "updated_at": now,
        }

        # Store chunks with vector embeddings and content hashes
        stored_chunks: list[dict] = []
        for chunk in parsed_resume.chunks:
            chunk_dict = {
                "id": chunk.id,
                "resume_id": parsed_resume.id,
                "user_id": user_id,
                "section_type": chunk.section_type,
                "content": chunk.content,
                "chunk_index": chunk.chunk_index,
                "content_hash": chunk.content_hash,
                "embedding": chunk.embedding,
                "created_at": now,
            }
            stored_chunks.append(chunk_dict)

            # Record in embedding metadata store if vector exists
            if chunk.embedding and chunk.content_hash:
                rec_key = f"{chunk.content_hash}:{settings.ollama_embedding_model}:{settings.embedding_dimensions}"
                cls._embedding_records[rec_key] = {
                    "id": chunk.id,
                    "user_id": user_id,
                    "entity_type": "RESUME_CHUNK",
                    "entity_id": chunk.id,
                    "source_type": "RESUME",
                    "source_id": parsed_resume.id,
                    "model_name": settings.ollama_embedding_model,
                    "model_version": "v1",
                    "dimensions": settings.embedding_dimensions,
                    "content_hash": chunk.content_hash,
                    "embedding": chunk.embedding,
                    "created_at": now,
                }

        cls._chunks[resume_id_str] = stored_chunks

        # Store claims
        stored_claims: list[dict] = []
        for claim in parsed_resume.claims:
            stored_claims.append(
                {
                    "id": claim.id,
                    "resume_id": parsed_resume.id,
                    "user_id": user_id,
                    "claim_type": claim.claim_type,
                    "statement": claim.statement,
                    "source_type": claim.source_type,
                    "source_id": claim.source_id,
                    "evidence_text": claim.evidence_text,
                    "verification_status": claim.verification_status,
                    "confidence_score": claim.confidence_score,
                    "allowed_in_tailoring": claim.allowed_in_tailoring,
                    "created_at": now,
                    "updated_at": now,
                }
            )
        cls._claims[resume_id_str] = stored_claims

        return parsed_resume

    @classmethod
    async def get_resume(
        cls,
        resume_id: UUID,
        user: AuthenticatedUser,
    ) -> dict | None:
        """
        Fetch resume record enforcing user ownership (RLS equivalent).
        """
        resume_id_str = str(resume_id)
        resume_data = cls._resumes.get(resume_id_str)
        if not resume_data:
            return None

        # RLS check: User A must never access User B's resume
        if resume_data["user_id"] != user.user_id:
            raise CareerOSError(
                code="FORBIDDEN",
                message="Access denied to resume belonging to another user",
                status_code=403,
            )

        return resume_data

    @classmethod
    async def get_claims_by_resume_id(
        cls,
        resume_id: UUID,
        user: AuthenticatedUser,
    ) -> list[ResumeClaim]:
        """
        Fetch verifiable claims for a resume enforcing user ownership.
        """
        resume = await cls.get_resume(resume_id, user)
        if not resume:
            raise CareerOSError(
                code="RESUME_NOT_FOUND",
                message=f"Resume with ID '{resume_id}' was not found",
                status_code=404,
            )

        resume_id_str = str(resume_id)
        claims_data = cls._claims.get(resume_id_str, [])

        return [
            ResumeClaim(
                id=c["id"],
                resume_id=c["resume_id"],
                claim_type=c["claim_type"],
                statement=c["statement"],
                source_type=c["source_type"],
                source_id=c.get("source_id"),
                evidence_text=c["evidence_text"],
                verification_status=c["verification_status"],
                confidence_score=c["confidence_score"],
                allowed_in_tailoring=c["allowed_in_tailoring"],
            )
            for c in claims_data
        ]

    @classmethod
    async def get_user_chunks_with_embeddings(
        cls,
        user_id: UUID,
        entity_type: str | None = None,
    ) -> list[dict]:
        """
        Retrieve all chunks belonging to a specific user that contain embeddings.
        Enforces strict user isolation.
        """
        matched_chunks: list[dict] = []
        for resume_id_str, chunks_list in cls._chunks.items():
            # Verify resume ownership
            resume = cls._resumes.get(resume_id_str)
            if not resume or resume["user_id"] != user_id:
                continue

            for ch in chunks_list:
                if ch.get("embedding"):
                    chunk_copy = dict(ch)
                    chunk_copy["file_name"] = resume.get("file_name")
                    chunk_copy["entity_type"] = "RESUME_CHUNK"
                    matched_chunks.append(chunk_copy)

        return matched_chunks

    @classmethod
    async def get_resume_embedding_status(
        cls,
        resume_id: UUID,
        user: AuthenticatedUser,
    ) -> dict:
        """
        Retrieve embedding status for a resume's chunks.
        """
        resume = await cls.get_resume(resume_id, user)
        if not resume:
            raise CareerOSError(
                code="RESUME_NOT_FOUND",
                message=f"Resume with ID '{resume_id}' was not found",
                status_code=404,
            )

        resume_id_str = str(resume_id)
        chunks = cls._chunks.get(resume_id_str, [])
        total_chunks = len(chunks)
        embedded_chunks = sum(1 for c in chunks if c.get("embedding"))

        return {
            "resume_id": resume_id,
            "file_name": resume.get("file_name"),
            "total_chunks": total_chunks,
            "embedded_chunks": embedded_chunks,
            "model_name": settings.ollama_embedding_model,
            "dimensions": settings.embedding_dimensions,
            "status": "READY"
            if total_chunks > 0 and embedded_chunks == total_chunks
            else "PENDING",
        }
