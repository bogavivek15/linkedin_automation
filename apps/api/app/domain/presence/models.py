from enum import Enum
from typing import Optional, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field

class ContentType(str, Enum):
    LINKEDIN_POST = "LINKEDIN_POST"
    BLOG_POST = "BLOG_POST"
    TWEET = "TWEET"

class PublicationMode(str, Enum):
    SANDBOX = "SANDBOX"
    LIVE = "LIVE"
    USER_HANDOFF = "USER_HANDOFF"

class PostStatus(str, Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PUBLISHED = "PUBLISHED"

class ContentIdea(BaseModel):
    id: str
    title: str
    summary: str
    target_audience: str
    suggested_type: ContentType
    confidence_score: float

class PresencePost(BaseModel):
    id: str
    user_id: str
    profile_id: str
    title: str
    content_body: str
    image_url: Optional[str] = None
    content_type: ContentType = ContentType.LINKEDIN_POST
    publication_mode: PublicationMode = PublicationMode.SANDBOX
    validation_status: PostStatus = PostStatus.PENDING_REVIEW
    grounding_evidence_ids: list[str] = Field(default_factory=list)
    quality_score: float = 0.0
    publication_evidence: Optional[dict[str, Any]] = None
    scheduled_for: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    published_at: Optional[datetime] = None
