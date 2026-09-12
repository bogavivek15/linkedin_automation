"""
CareerOS Phase 13 — Career Learning & Feedback Loop Service.

Coordinates closed-loop learning from application outcomes into empirical patterns and actionable insights.
"""

from uuid import UUID

from apps.api.app.domain.learning.insights import CareerInsightGenerator
from apps.api.app.domain.learning.models import (
    CareerInsight,
    CareerOutcome,
    CareerPattern,
)
from apps.api.app.domain.learning.patterns import OutcomePatternDetector
from apps.api.app.repositories.learning_repository import LearningRepository


class LearningService:
    """
    Coordinates empirical learning loops from application outcomes.
    """

    async def record_outcome(
        self,
        outcome: CareerOutcome,
        user_id: UUID,
    ) -> tuple[CareerOutcome, list[CareerPattern], list[CareerInsight]]:
        """
        Record an outcome and automatically trigger pattern and insight synthesis.
        """
        saved_outcome = await LearningRepository.save_outcome(outcome, user_id)

        # Trigger analysis
        patterns, insights = await self.run_feedback_analysis(
            profile_id=outcome.profile_id,
            user_id=user_id,
        )

        return saved_outcome, patterns, insights

    async def run_feedback_analysis(
        self,
        profile_id: str,
        user_id: UUID,
    ) -> tuple[list[CareerPattern], list[CareerInsight]]:
        """
        Run empirical pattern detection and insight generation across recorded outcomes.
        """
        outcomes = await LearningRepository.list_outcomes(user_id, profile_id)
        patterns = OutcomePatternDetector.detect_patterns(
            user_id=str(user_id),
            profile_id=profile_id,
            outcomes=outcomes,
        )
        await LearningRepository.save_patterns(patterns, user_id)

        insights = CareerInsightGenerator.generate_insights(
            user_id=str(user_id),
            profile_id=profile_id,
            patterns=patterns,
        )
        await LearningRepository.save_insights(insights, user_id)

        return patterns, insights

    async def list_outcomes(self, user_id: UUID, profile_id: str | None = None) -> list[CareerOutcome]:
        return await LearningRepository.list_outcomes(user_id, profile_id)

    async def list_patterns(self, user_id: UUID, profile_id: str | None = None) -> list[CareerPattern]:
        return await LearningRepository.list_patterns(user_id, profile_id)

    async def list_insights(
        self,
        user_id: UUID,
        profile_id: str | None = None,
        include_dismissed: bool = False,
    ) -> list[CareerInsight]:
        return await LearningRepository.list_insights(user_id, profile_id, include_dismissed)

    async def dismiss_insight(self, insight_id: str, user_id: UUID) -> bool:
        return await LearningRepository.dismiss_insight(insight_id, user_id)
