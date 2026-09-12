from apps.api.app.core.security import AuthenticatedUser, get_current_user
from apps.api.app.domain.resume.models import SemanticSearchResult
from apps.api.app.services.embedding.search import SemanticSearchService
from fastapi import APIRouter, Depends, Query, Request

router = APIRouter(prefix="/search", tags=["Semantic Search & Retrieval"])


@router.get("/semantic")
async def semantic_search(
    request: Request,
    q: str = Query(..., min_length=1, max_length=1000, description="Natural language search query"),
    entity_type: str | None = Query(
        None, description="Filter by entity type (e.g. RESUME_CHUNK, PROJECT)"
    ),
    limit: int = Query(10, ge=1, le=50, description="Max results to return"),
    min_similarity: float = Query(
        0.0, ge=0.0, le=1.0, description="Minimum cosine similarity threshold"
    ),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Perform cosine semantic similarity search over career assets.
    Strictly isolated to the authenticated user's records.
    Never exposes raw vector embeddings.
    """
    request_id = getattr(request.state, "request_id", "req-test")

    results: list[SemanticSearchResult] = await SemanticSearchService.search(
        query=q,
        current_user=current_user,
        entity_type=entity_type,
        limit=limit,
        min_similarity=min_similarity,
    )

    return {
        "success": True,
        "data": [r.model_dump(mode="json") for r in results],
        "error": None,
        "meta": {
            "request_id": request_id,
            "query": q,
            "total_results": len(results),
            "limit": limit,
            "min_similarity": min_similarity,
            "entity_type": entity_type,
        },
    }
