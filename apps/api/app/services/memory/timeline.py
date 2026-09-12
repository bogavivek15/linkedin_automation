"""
CareerOS Phase 4 — Career Memory Timeline Service.

Constructs a human-readable, chronologically ordered timeline of:
- verified skills & candidate confirmations
- detected project & GitHub milestones
- application outcomes & learning gap insights
- credential & coursework evidence
"""

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from apps.api.app.domain.memory.models import CareerMemoryRecord
from apps.api.app.repositories.lifecycle_repository import LifecycleRepository
from apps.api.app.services.memory.service import MemoryService


class TimelineEntry(BaseModel):
    id: str
    timestamp: datetime
    formatted_date: str
    badge_type: Literal["VERIFIED", "USER_CONFIRMED", "LEARNING_GAP", "PROJECT", "MILESTONE", "APPLICATION"]
    title: str
    summary: str
    evidence: str | None = None
    provenance: str | None = None
    verification_status: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class CareerMemoryTimelineService:
    """
    Assembles Career Memory records and lifecycle events into an intuitive audit timeline.
    """

    def __init__(self, memory_service: MemoryService | None = None):
        self.memory_service = memory_service or MemoryService()

    async def get_timeline(
        self,
        user_id: UUID,
        profile_id: str | None = None,
        limit: int = 50,
    ) -> list[TimelineEntry]:
        """
        Produce a unified, reverse-chronological timeline of memory and career milestones.
        """
        memories = await self.memory_service.list_memories(user_id=user_id, profile_id=profile_id)
        entries: list[TimelineEntry] = []

        for m in memories:
            ts = m.created_at
            date_str = ts.strftime("%b %d")

            # Determine badge and clean display title
            badge: Literal["VERIFIED", "USER_CONFIRMED", "LEARNING_GAP", "PROJECT", "MILESTONE", "APPLICATION"] = "VERIFIED"
            if m.category == "LEARNING_GAP" or m.verification_status == "RECOMMENDED_LEARNING":
                badge = "LEARNING_GAP"
                title = f"→ {m.key.replace('learning_gap:', '').title()} identified as career opportunity gap"
            elif m.verification_status in ("USER_CONFIRMED", "STUDENT_CONFIRMED"):
                badge = "USER_CONFIRMED"
                title = f"✓ {m.key.replace('skill:', '').title()} confirmed by candidate"
            elif m.category == "PROJECT":
                badge = "PROJECT"
                title = f"✓ {m.key.replace('github_project:', '').replace('project:', '').title()} detected"
            elif m.category == "INSIGHT":
                badge = "MILESTONE"
                title = f"💡 Career intelligence: {m.key.replace('daily_insight:', '').title()}"
            else:
                title = f"✓ {m.key.replace('skill:', '').title()} verified"

            entries.append(
                TimelineEntry(
                    id=m.id,
                    timestamp=ts,
                    formatted_date=date_str,
                    badge_type=badge,
                    title=title,
                    summary=m.content,
                    evidence=m.evidence_ref or m.provenance,
                    provenance=m.provenance,
                    verification_status=m.verification_status,
                    metadata=m.metadata or {},
                )
            )

        # Ingest active lifecycle transitions for holistic context
        try:
            lifecycles = await LifecycleRepository.list_lifecycles_for_user(user_id)
            for lc in lifecycles:
                for tr in lc.transitions:
                    ts = tr.created_at
                    date_str = ts.strftime("%b %d")
                    entries.append(
                        TimelineEntry(
                            id=tr.id,
                            timestamp=ts,
                            formatted_date=date_str,
                            badge_type="APPLICATION",
                            title=f"📋 Application Status: {tr.to_status}",
                            summary=tr.notes or f"Application transitioned from {tr.from_status} to {tr.to_status}.",
                            evidence=f"Evidence: {tr.evidence_type}",
                            provenance="Application Lifecycle State Machine",
                            verification_status="EVIDENCE_VALIDATED",
                            metadata={"from": tr.from_status, "to": tr.to_status},
                        )
                    )
        except Exception:
            pass

        # Sort descending by timestamp
        entries.sort(key=lambda x: x.timestamp, reverse=True)
        return entries[:limit]
