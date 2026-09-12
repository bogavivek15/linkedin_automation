import asyncio
import hashlib
import math
import random
from abc import ABC, abstractmethod
from typing import Any

import httpx
from apps.api.app.core.config import settings
from apps.api.app.core.errors import CareerOSError
from apps.api.app.core.logging import logger
from apps.api.app.services.embedding.validation import validate_vector


class EmbeddingProvider(ABC):
    """
    Abstract contract for 768-dimensional semantic embedding providers.
    """

    @property
    @abstractmethod
    def model_name(self) -> str:
        pass

    @property
    @abstractmethod
    def dimensions(self) -> int:
        pass

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Embed a single text string into a 768-dim float vector."""
        pass

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of text strings into 768-dim float vectors."""
        pass


class MockEmbeddingProvider(EmbeddingProvider):
    """
    Deterministic, offline mock embedding provider for tests and zero-network execution.
    Generates unit-normalized 768-dim vectors seeded by SHA-256 of the input text.
    Guarantees:
    - Exactly 768 dimensions.
    - Same text -> identical vector.
    - Zero external dependencies or network calls.
    """

    def __init__(self, model_name: str = "mock-nomic-embed-text", dimensions: int = 768):
        self._model_name = model_name
        self._dimensions = dimensions

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def _generate_deterministic_vector(self, text: str) -> list[float]:
        # Hash text to create a stable 64-bit integer seed
        hasher = hashlib.sha256(text.strip().encode("utf-8"))
        seed_int = int(hasher.hexdigest()[:16], 16)
        rng = random.Random(seed_int)

        # Generate pseudo-random vector with standard normal distribution
        raw_vec = [rng.gauss(0.0, 1.0) for _ in range(self._dimensions)]

        # L2-normalize vector for accurate cosine similarity
        norm = math.sqrt(sum(x * x for x in raw_vec))
        if norm > 0:
            raw_vec = [x / norm for x in raw_vec]

        return validate_vector(raw_vec, self._dimensions)

    async def embed(self, text: str) -> list[float]:
        if not text or not text.strip():
            raise CareerOSError(
                code="EMBEDDING_INVALID_VECTOR",
                message="Cannot embed empty or whitespace-only text",
                status_code=400,
            )
        return self._generate_deterministic_vector(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors: list[list[float]] = []
        for t in texts:
            vectors.append(await self.embed(t))
        return vectors


class OllamaEmbeddingProvider(EmbeddingProvider):
    """
    Local-first Ollama embedding provider for 'nomic-embed-text'.
    Supports bounded exponential backoff retries and timeouts.
    """

    def __init__(
        self,
        base_url: str | None = None,
        model_name: str | None = None,
        dimensions: int | None = None,
        timeout: float | None = None,
        max_retries: int = 3,
    ):
        self._base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self._model_name = model_name or settings.ollama_embedding_model
        self._dimensions = dimensions or settings.embedding_dimensions
        self._timeout = timeout or settings.embedding_timeout_seconds
        self._max_retries = max_retries

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def _post_with_retry(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        last_exception: Exception | None = None
        delay = 0.5

        for attempt in range(1, self._max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    resp = await client.post(f"{self._base_url}{endpoint}", json=payload)
                    if resp.status_code == 200:
                        return resp.json()
                    if resp.status_code in (404, 400):
                        # Client / model not found error, do not retry
                        raise CareerOSError(
                            code="EMBEDDING_PROVIDER_UNAVAILABLE",
                            message=f"Ollama error {resp.status_code}: {resp.text}",
                            status_code=503,
                        )
                    resp.raise_for_status()
            except httpx.TimeoutException as exc:
                last_exception = exc
                logger.warning(
                    f"Ollama request timeout on attempt {attempt}/{self._max_retries}",
                    extra={"attempt": attempt, "endpoint": endpoint},
                )
            except (httpx.ConnectError, httpx.NetworkError) as exc:
                last_exception = exc
                logger.warning(
                    f"Ollama connection error on attempt {attempt}/{self._max_retries}",
                    extra={"attempt": attempt, "endpoint": endpoint},
                )
            except CareerOSError:
                raise
            except Exception as exc:
                last_exception = exc
                logger.warning(f"Unexpected Ollama communication error: {exc!s}")

            if attempt < self._max_retries:
                await asyncio.sleep(delay)
                delay *= 2

        if isinstance(last_exception, httpx.TimeoutException):
            raise CareerOSError(
                code="EMBEDDING_TIMEOUT",
                message=f"Embedding provider timed out after {self._timeout}s across {self._max_retries} attempts",
                status_code=504,
            )
        raise CareerOSError(
            code="EMBEDDING_PROVIDER_UNAVAILABLE",
            message=f"Ollama embedding provider unavailable at {self._base_url}: {last_exception!s}",
            status_code=503,
        )

    async def embed(self, text: str) -> list[float]:
        if not text or not text.strip():
            raise CareerOSError(
                code="EMBEDDING_INVALID_VECTOR",
                message="Cannot embed empty or whitespace-only text",
                status_code=400,
            )

        # Try modern /api/embed first, fallback to /api/embeddings
        try:
            res = await self._post_with_retry(
                "/api/embed",
                {"model": self._model_name, "input": [text]},
            )
            raw_embeddings = res.get("embeddings", [])
            if raw_embeddings:
                return validate_vector(raw_embeddings[0], self._dimensions)
        except Exception:
            pass

        # Fallback to legacy /api/embeddings
        res = await self._post_with_retry(
            "/api/embeddings",
            {"model": self._model_name, "prompt": text},
        )
        raw_vec = res.get("embedding")
        return validate_vector(raw_vec, self._dimensions)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        cleaned_texts = [t.strip() for t in texts if t and t.strip()]
        if not cleaned_texts:
            return []

        # Use /api/embed batch endpoint
        try:
            res = await self._post_with_retry(
                "/api/embed",
                {"model": self._model_name, "input": cleaned_texts},
            )
            raw_embeddings = res.get("embeddings", [])
            if len(raw_embeddings) == len(cleaned_texts):
                return [validate_vector(v, self._dimensions) for v in raw_embeddings]
        except Exception:
            pass

        # Fallback: sequential embed
        vectors: list[list[float]] = []
        for t in cleaned_texts:
            v = await self.embed(t)
            vectors.append(v)
        return vectors


def get_embedding_provider(force_mock: bool = False) -> EmbeddingProvider:
    """
    Factory returning the active embedding provider.
    Uses MockEmbeddingProvider in test/demo environments or when explicitly requested.
    """
    if force_mock or settings.app_env == "test" or settings.demo_mode:
        return MockEmbeddingProvider(
            model_name=settings.ollama_embedding_model,
            dimensions=settings.embedding_dimensions,
        )
    return OllamaEmbeddingProvider()
