import re
from uuid import UUID, uuid4

from apps.api.app.core.config import settings
from apps.api.app.domain.resume.models import ResumeChunk


def semantic_chunk_section(
    content: str,
    max_chunk_chars: int | None = None,
    overlap_chars: int | None = None,
) -> list[str]:
    """
    Split a section into coherent paragraphs / bullet chunks.
    If a section or block exceeds max_chunk_chars, split along sentence or newline boundaries
    while preserving overlap to prevent loss of semantic context.
    """
    max_len = max_chunk_chars or settings.embedding_chunk_size
    overlap = overlap_chars or settings.embedding_chunk_overlap

    if not content or not content.strip():
        return []

    # Try splitting by double-newline or bullet points first
    blocks = [b.strip() for b in re.split(r"\n\s*\n|(?<=\n)(?=[•\-\*]\s+)", content) if b.strip()]

    chunks: list[str] = []
    current_chunk: list[str] = []
    current_len = 0

    for block in blocks:
        block_len = len(block)
        if current_len + block_len + 1 <= max_len:
            current_chunk.append(block)
            current_len += block_len + 1
        else:
            if current_chunk:
                chunks.append("\n".join(current_chunk).strip())
            # If a single block itself exceeds max_len, split by sentence or character window
            if block_len > max_len:
                start = 0
                while start < block_len:
                    end = min(start + max_len, block_len)
                    # Try to break on whitespace or sentence end
                    if end < block_len:
                        break_pos = block.rfind(". ", start, end)
                        if break_pos != -1 and break_pos > start + 100:
                            end = break_pos + 1
                        else:
                            space_pos = block.rfind(" ", start, end)
                            if space_pos != -1 and space_pos > start + 100:
                                end = space_pos
                    segment = block[start:end].strip()
                    if segment:
                        chunks.append(segment)
                    start = end - overlap if end < block_len else end
                current_chunk = []
                current_len = 0
            else:
                current_chunk = [block]
                current_len = block_len

    if current_chunk:
        chunks.append("\n".join(current_chunk).strip())

    return [c for c in chunks if c.strip()]


def create_section_aware_chunks(
    resume_id: UUID,
    sections: dict[str, str],
    user_id: UUID | None = None,
    max_chunk_chars: int | None = None,
    overlap_chars: int | None = None,
) -> list[ResumeChunk]:
    """
    Create section-aware ResumeChunk domain models preserving lineage and order.
    """
    chunks: list[ResumeChunk] = []
    chunk_index = 0

    for sec_name, sec_content in sections.items():
        sub_chunks = semantic_chunk_section(
            sec_content,
            max_chunk_chars=max_chunk_chars,
            overlap_chars=overlap_chars,
        )

        for sub_text in sub_chunks:
            chunks.append(
                ResumeChunk(
                    id=uuid4(),
                    resume_id=resume_id,
                    user_id=user_id,
                    section_type=sec_name,  # type: ignore
                    content=sub_text,
                    chunk_index=chunk_index,
                )
            )
            chunk_index += 1

    return chunks
