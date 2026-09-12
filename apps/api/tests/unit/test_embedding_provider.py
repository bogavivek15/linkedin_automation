import math

import pytest
from apps.api.app.core.errors import CareerOSError
from apps.api.app.services.embedding.provider import (
    MockEmbeddingProvider,
    OllamaEmbeddingProvider,
)
from apps.api.app.services.embedding.service import EmbeddingService
from apps.api.app.services.embedding.validation import validate_vector


@pytest.mark.asyncio
async def test_mock_provider_exact_dimensions():
    provider = MockEmbeddingProvider()
    vec = await provider.embed("Python FastAPI Backend Engineer")
    assert len(vec) == 768
    assert all(isinstance(x, float) for x in vec)
    # Verify L2 normalization (norm ~ 1.0)
    norm = math.sqrt(sum(x * x for x in vec))
    assert math.isclose(norm, 1.0, rel_tol=1e-4)


@pytest.mark.asyncio
async def test_mock_provider_deterministic_output():
    provider = MockEmbeddingProvider()
    text = "Building autonomous multi-agent systems with LangGraph"
    vec1 = await provider.embed(text)
    vec2 = await provider.embed(text)
    assert vec1 == vec2


@pytest.mark.asyncio
async def test_mock_provider_batch_output():
    provider = MockEmbeddingProvider()
    texts = ["First chunk", "Second chunk", "Third chunk"]
    vecs = await provider.embed_batch(texts)
    assert len(vecs) == 3
    for v in vecs:
        assert len(v) == 768


@pytest.mark.asyncio
async def test_reject_empty_text():
    provider = MockEmbeddingProvider()
    with pytest.raises(CareerOSError) as exc:
        await provider.embed("")
    assert exc.value.code == "EMBEDDING_INVALID_VECTOR"

    with pytest.raises(CareerOSError) as exc:
        await provider.embed("   ")
    assert exc.value.code == "EMBEDDING_INVALID_VECTOR"


def test_vector_validation_dimension_mismatch():
    with pytest.raises(CareerOSError) as exc:
        validate_vector([0.1] * 512, expected_dimensions=768)
    assert exc.value.code == "EMBEDDING_DIMENSION_MISMATCH"

    with pytest.raises(CareerOSError) as exc:
        validate_vector([0.1] * 1024, expected_dimensions=768)
    assert exc.value.code == "EMBEDDING_DIMENSION_MISMATCH"


def test_vector_validation_nan_and_inf():
    bad_nan = [0.1] * 767 + [float("nan")]
    with pytest.raises(CareerOSError) as exc:
        validate_vector(bad_nan, expected_dimensions=768)
    assert exc.value.code == "EMBEDDING_INVALID_VECTOR"

    bad_inf = [0.1] * 767 + [float("inf")]
    with pytest.raises(CareerOSError) as exc:
        validate_vector(bad_inf, expected_dimensions=768)
    assert exc.value.code == "EMBEDDING_INVALID_VECTOR"


def test_vector_validation_non_numeric():
    bad_str = [0.1] * 767 + ["invalid_str"]
    with pytest.raises(CareerOSError) as exc:
        validate_vector(bad_str, expected_dimensions=768)
    assert exc.value.code == "EMBEDDING_INVALID_VECTOR"


def test_deterministic_content_hashing():
    hash1 = EmbeddingService.compute_content_hash("Senior Python Architect")
    hash2 = EmbeddingService.compute_content_hash("Senior Python Architect")
    hash3 = EmbeddingService.compute_content_hash("Different Text Content")
    assert hash1 == hash2
    assert hash1 != hash3
    assert len(hash1) == 64  # SHA-256 hex string


@pytest.mark.asyncio
async def test_ollama_provider_unavailable_handling():
    # Attempting to call an unreachable port triggers clean EMBEDDING_PROVIDER_UNAVAILABLE
    provider = OllamaEmbeddingProvider(
        base_url="http://127.0.0.1:59999",
        timeout=0.2,
        max_retries=1,
    )
    with pytest.raises(CareerOSError) as exc:
        await provider.embed("Test text")
    assert exc.value.code in ("EMBEDDING_PROVIDER_UNAVAILABLE", "EMBEDDING_TIMEOUT")
