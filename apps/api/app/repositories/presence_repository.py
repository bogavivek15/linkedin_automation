"""
CareerOS Phase 15 — Professional Presence Repository.

Multi-tenant isolated repository for presence drafts, scheduled posts,
and published records matching 027_presence_agents.sql.
"""

from typing import Any
from uuid import UUID

from apps.api.app.domain.presence.models import PresencePost


class PresenceRepository:
    """
    Persistence layer for presence posts and content drafts.
    """

    _posts: dict[str, dict[str, Any]] = {}

    @classmethod
    def reset_store(cls) -> None:
        """Helper for test isolation."""
        cls._posts.clear()

    @classmethod
    async def save_post(
        cls,
        post: PresencePost,
        user_id: UUID,
    ) -> PresencePost:
        """
        Upsert a presence post with tenant scoping.
        """
        post_id = str(post.id)
        user_str = str(user_id)

        doc = {
            "id": post_id,
            "user_id": user_str,
            "profile_id": str(post.profile_id),
            "content_type": post.content_type,
            "title": post.title,
            "content_body": post.content_body,
            "grounding_evidence_ids": [str(eid) for eid in post.grounding_evidence_ids],
            "quality_score": post.quality_score,
            "validation_status": post.validation_status,
            "publication_mode": post.publication_mode,
            "publication_evidence": post.publication_evidence,
            "scheduled_for": post.scheduled_for,
            "published_at": post.published_at,
            "created_at": post.created_at,
            "updated_at": post.updated_at,
            "_raw_model": post,
        }

        cls._posts[post_id] = doc
        return post

    @classmethod
    async def get_post(
        cls,
        post_id: str,
        user_id: UUID,
    ) -> PresencePost | None:
        """
        Retrieve post by ID enforcing user isolation.
        """
        doc = cls._posts.get(str(post_id))
        if not doc or doc["user_id"] != str(user_id):
            return None
        return doc["_raw_model"]

    @classmethod
    async def list_posts(
        cls,
        user_id: UUID,
        profile_id: str | None = None,
        status: str | None = None,
    ) -> list[PresencePost]:
        """
        List posts for user with optional profile and status filtering.
        """
        user_str = str(user_id)
        results: list[PresencePost] = []
        for doc in cls._posts.values():
            if doc["user_id"] == user_str:
                if profile_id and doc["profile_id"] != profile_id:
                    continue
                if status and doc["validation_status"] != status:
                    continue
                results.append(doc["_raw_model"])
        return sorted(results, key=lambda x: x.created_at, reverse=True)

    @classmethod
    async def delete_post(
        cls,
        post_id: str,
        user_id: UUID,
    ) -> bool:
        """
        Delete a presence post enforcing user isolation.
        """
        doc = cls._posts.get(str(post_id))
        if not doc or doc["user_id"] != str(user_id):
            return False
        cls._posts.pop(str(post_id), None)
        return True
