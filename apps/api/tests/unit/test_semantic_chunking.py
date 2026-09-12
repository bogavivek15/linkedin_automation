from uuid import uuid4

from apps.api.app.services.embedding.chunking import (
    create_section_aware_chunks,
    semantic_chunk_section,
)


def test_chunking_preserves_sections_and_lineage():
    resume_id = uuid4()
    user_id = uuid4()
    sections = {
        "SUMMARY": "Experienced software engineer specializing in autonomous agent architectures.",
        "EXPERIENCE": "Antigravity Systems - Senior AI Engineer\n- Led development of pgvector RAG pipeline",
        "SKILLS": "Python, TypeScript, FastAPI, PostgreSQL, LangGraph",
    }

    chunks = create_section_aware_chunks(
        resume_id=resume_id,
        sections=sections,
        user_id=user_id,
    )

    assert len(chunks) == 3
    assert chunks[0].section_type == "SUMMARY"
    assert chunks[0].resume_id == resume_id
    assert chunks[0].user_id == user_id
    assert chunks[0].chunk_index == 0

    assert chunks[1].section_type == "EXPERIENCE"
    assert chunks[1].chunk_index == 1

    assert chunks[2].section_type == "SKILLS"
    assert chunks[2].chunk_index == 2


def test_long_section_splitting_with_overlap():
    long_content = "\n".join(
        [
            f"Bullet point {i}: detailed description of software feature and metrics achieved."
            for i in range(25)
        ]
    )
    sub_chunks = semantic_chunk_section(
        long_content,
        max_chunk_chars=200,
        overlap_chars=30,
    )

    assert len(sub_chunks) > 1
    for chunk in sub_chunks:
        assert len(chunk) <= 300  # bounded chunk size


def test_empty_section_handling():
    chunks = semantic_chunk_section("")
    assert chunks == []

    chunks_whitespace = semantic_chunk_section("    \n\n   ")
    assert chunks_whitespace == []
