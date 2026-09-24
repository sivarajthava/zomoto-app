"""Orchestrator service coordinating Stage 1 retrieval and Stage 2 AI reasoning."""

from __future__ import annotations

import logging
import time
from typing import Optional

from app.models import RecommendationResponse, UserPreferenceRequest
from app.services.filter_service import FilterService
from app.services.llm_service import LLMService, get_llm_service

logger = logging.getLogger(__name__)


class RecommendationOrchestrator:
    """Coordinates end-to-end recommendation workflow from candidate pruning to LLM ranking."""

    def __init__(
        self,
        filter_service: Optional[FilterService] = None,
        llm_service: Optional[LLMService] = None,
    ):
        self.filter_service = filter_service or FilterService()
        self.llm_service = llm_service or get_llm_service()

    async def get_recommendations(
        self, request: UserPreferenceRequest
    ) -> RecommendationResponse:
        """Execute two-stage hybrid recommendation pipeline."""
        start_time = time.perf_counter()

        # Stage 1: Fast deterministic candidate retrieval
        candidates, is_relaxed = self.filter_service.filter_candidates(request)
        stage_1_ms = (time.perf_counter() - start_time) * 1000

        if not candidates:
            logger.warning(f"Zero candidates found for location: {request.location}")
            return RecommendationResponse(
                summary=(
                    f"No matching restaurants found in '{request.location}'. "
                    "Please check the location name or try a supported city like Bangalore."
                ),
                is_fallback=True,
                recommendations=[],
            )

        # Stage 2: Contextual re-ranking & explanation generation
        llm_start = time.perf_counter()
        response = await self.llm_service.rank_and_explain(
            request=request,
            candidates=candidates,
            is_relaxed=is_relaxed,
        )
        stage_2_ms = (time.perf_counter() - llm_start) * 1000
        total_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            f"Recommendation completed in {total_ms:.2f}ms "
            f"(Stage 1: {stage_1_ms:.2f}ms, Stage 2: {stage_2_ms:.2f}ms, "
            f"candidates={len(candidates)}, is_fallback={response.is_fallback})"
        )

        return response


def get_recommendation_service() -> RecommendationOrchestrator:
    """Dependency helper returning a RecommendationOrchestrator instance."""
    return RecommendationOrchestrator()
