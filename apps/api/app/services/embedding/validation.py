import math
from typing import Any

from apps.api.app.core.config import settings
from apps.api.app.core.errors import CareerOSError


def validate_vector(
    vector: Any,
    expected_dimensions: int | None = None,
) -> list[float]:
    """
    Strict validation of embedding vectors before persistence or mathematical operations.
    Rejects:
    - Non-lists / None
    - Length != expected_dimensions (default 768)
    - NaN, Infinity, -Infinity
    - Non-numeric / strings
    Never silently pads or truncates.
    """
    target_dim = expected_dimensions or settings.embedding_dimensions

    if vector is None or not isinstance(vector, (list, tuple)):
        raise CareerOSError(
            code="EMBEDDING_INVALID_VECTOR",
            message="Embedding vector must be a non-empty sequence of floating point numbers",
            status_code=422,
        )

    if len(vector) != target_dim:
        raise CareerOSError(
            code="EMBEDDING_DIMENSION_MISMATCH",
            message=f"Embedding dimensions mismatch: expected {target_dim}, received {len(vector)}",
            status_code=422,
        )

    validated_floats: list[float] = []
    for i, val in enumerate(vector):
        if val is None or isinstance(val, (str, bool)):
            raise CareerOSError(
                code="EMBEDDING_INVALID_VECTOR",
                message=f"Vector contains invalid non-numeric element at index {i}",
                status_code=422,
            )
        try:
            float_val = float(val)
        except (ValueError, TypeError):
            raise CareerOSError(
                code="EMBEDDING_INVALID_VECTOR",
                message=f"Vector element at index {i} cannot be converted to float",
                status_code=422,
            )

        if math.isnan(float_val) or math.isinf(float_val):
            raise CareerOSError(
                code="EMBEDDING_INVALID_VECTOR",
                message=f"Vector contains non-finite float (NaN or Inf) at index {i}",
                status_code=422,
            )

        validated_floats.append(float_val)

    return validated_floats
