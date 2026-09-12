"""
Unit tests for CareerOS Phase 14 — Memory Contextual Retrieval Engine.
"""

from apps.api.app.domain.memory.models import CareerMemoryRecord
from apps.api.app.domain.memory.retrieval import CareerMemoryRetriever


def test_retrieval_filters_unverified_records_for_applications():
    user_id = "00000000-0000-0000-0000-000000000001"
    records = [
        CareerMemoryRecord(
            user_id=user_id,
            profile_id="prof-1",
            category="PROJECT",
            key="proj_rag",
            content="Built RAG with Supabase pgvector",
            provenance="Verified Git commit",
            confidence=0.95,
            verification_status="USER_CONFIRMED",
        ),
        CareerMemoryRecord(
            user_id=user_id,
            profile_id="prof-1",
            category="SKILL",
            key="skill_fastapi",
            content="FastAPI async microservices",
            provenance="Verified production repo",
            confidence=0.9,
            verification_status="EVIDENCE_VALIDATED",
        ),
        CareerMemoryRecord(
            user_id=user_id,
            profile_id="prof-1",
            category="SKILL",
            key="unverified_skill",
            content="Quantum computing algorithmic synthesis",
            provenance="Hallucinated claim",
            confidence=0.3,
            verification_status="AI_PROPOSED",
        ),
    ]

    app_context = CareerMemoryRetriever.retrieve_for_application(records)

    # UNVERIFIED / AI_PROPOSED below threshold must not be included
    assert len(app_context["projects"]) == 1
    assert app_context["projects"][0].key == "proj_rag"
    assert len(app_context["skills"]) == 1
    assert app_context["skills"][0].key == "skill_fastapi"
    # Unverified skill was excluded
    assert not any(s.key == "unverified_skill" for s in app_context["skills"])


def test_retrieval_filters_high_confidence_for_presence():
    user_id = "00000000-0000-0000-0000-000000000001"
    records = [
        CareerMemoryRecord(
            user_id=user_id,
            profile_id="prof-1",
            category="INSIGHT",
            key="scale_insight",
            content="Scaling Redis cluster to 100k QPS",
            provenance="System performance log",
            confidence=0.85,
            verification_status="EVIDENCE_VALIDATED",
        ),
        CareerMemoryRecord(
            user_id=user_id,
            profile_id="prof-1",
            category="INSIGHT",
            key="low_conf_insight",
            content="Speculative benchmark",
            provenance="Incomplete test",
            confidence=0.6,
            verification_status="EVIDENCE_VALIDATED",
        ),
    ]

    presence_items = CareerMemoryRetriever.retrieve_for_presence(records)

    assert len(presence_items) == 1
    assert presence_items[0].key == "scale_insight"
