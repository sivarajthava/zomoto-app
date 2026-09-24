"""Stage 2: AI reasoning, prompt engineering, and structured recommendation engine via Groq."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import List, Optional, Set

from groq import AsyncGroq

from app.config import settings
from app.models import (
    RecommendationResponse,
    Restaurant,
    RestaurantRecommendation,
    UserPreferenceRequest,
)

logger = logging.getLogger(__name__)


class FallbackRankingEngine:
    """Deterministic, metadata-driven recommendation engine for offline/fallback mode."""

    @staticmethod
    def rank_and_explain(
        request: UserPreferenceRequest,
        candidates: List[Restaurant],
        is_relaxed: bool = False,
    ) -> RecommendationResponse:
        """Produce structured recommendations with templated explanations."""
        if not candidates:
            return RecommendationResponse(
                summary=f"No matching restaurants found in {request.location}.",
                is_fallback=True,
                recommendations=[],
            )

        top_candidates = candidates[: min(5, len(candidates))]
        recs: List[RestaurantRecommendation] = []

        for idx, c in enumerate(top_candidates, 1):
            rating_str = f"{c.aggregate_rating:.1f}" if c.aggregate_rating else "Unrated"
            dishes_str = f" Popular dishes include {c.dish_liked}." if c.dish_liked else ""

            explanation = (
                f"{c.name} in {c.locality} is a top choice with a {rating_str} star rating "
                f"from {c.votes:,} diners. It serves {c.cuisines_str} and averages "
                f"INR {c.average_cost_for_two:.0f} for two, fitting your {c.budget_tier} budget."
                f"{dishes_str}"
            )

            recs.append(
                RestaurantRecommendation(
                    rank=idx,
                    restaurant_name=c.name,
                    cuisine=c.cuisines_str or "Multi-Cuisine",
                    rating=c.aggregate_rating if c.aggregate_rating else 3.5,
                    estimated_cost_for_two=c.average_cost_for_two,
                    explanation=explanation,
                )
            )

        relaxed_note = " (criteria expanded to find nearby options)" if is_relaxed else ""
        summary = (
            f"Curated {len(recs)} top restaurant recommendations in {request.location} "
            f"matching your {request.budget_tier} budget{relaxed_note}."
        )

        return RecommendationResponse(
            summary=summary,
            is_fallback=True,
            recommendations=recs,
        )


class LLMService:
    """Stage 2 AI reasoning engine powered by Groq LPU inference (openai/gpt-oss-120b)."""

    SYSTEM_INSTRUCTION = (
        "You are an expert food critic, culinary guide, and restaurant recommender. "
        "Your task is to analyze user preferences and rank the best-matching dining spots "
        "from the provided CANDIDATE LIST.\n\n"
        "STRICT GROUNDING RULE: You are strictly forbidden from inventing, hallucinating, "
        "or recommending any restaurant that is NOT present in the provided CANDIDATE LIST. "
        "Only recommend venues from the given candidates. Do not alter restaurant names.\n\n"
        "Provide insightful, personalized, human-like explanations detailing exactly WHY "
        "each restaurant satisfies the user's explicit criteria (location, budget, cuisine, rating) "
        "and contextual nuances (e.g., romance, outdoor seating, quick service, family dining).\n\n"
        "JSON OUTPUT REQUIREMENT:\n"
        "You must respond strictly with a valid JSON object matching the following structure:\n"
        "{\n"
        '  "summary": "A concise summary synthesizing why these spots match the user request",\n'
        '  "is_fallback": false,\n'
        '  "recommendations": [\n'
        "    {\n"
        '      "rank": 1,\n'
        '      "restaurant_name": "Exact Name from candidate list",\n'
        '      "cuisine": "Cuisines description",\n'
        '      "rating": 4.5,\n'
        '      "estimated_cost_for_two": 1200.0,\n'
        '      "explanation": "Compelling humanized explanation of why this restaurant fits."\n'
        "    }\n"
        "  ]\n"
        "}\n"
        "Do not output markdown backticks or text outside the JSON object."
    )

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        if api_key is not None:
            self.api_key = api_key
        else:
            self.api_key = settings.groq_api_key or settings.gemini_api_key
        self.model_name = model_name or settings.default_llm_model
        self.timeout = timeout or settings.request_timeout_seconds
        self.client: Optional[AsyncGroq] = None

        if (
            self.api_key
            and self.api_key.strip()
            and not self.api_key.startswith("your_")
        ):
            try:
                self.client = AsyncGroq(api_key=self.api_key, timeout=self.timeout)
            except Exception as e:
                logger.warning(f"Could not initialize Groq client: {e}")
                self.client = None

    async def rank_and_explain(
        self,
        request: UserPreferenceRequest,
        candidates: List[Restaurant],
        is_relaxed: bool = False,
    ) -> RecommendationResponse:
        """Evaluate candidates, rank them via Groq LPU, and generate structured explanations."""
        # 1. Fallback if client or candidates are not available
        if not self.client or not candidates:
            return FallbackRankingEngine.rank_and_explain(request, candidates, is_relaxed)

        prompt = self._build_prompt(request, candidates)

        # 2. Invoke Groq model with strict JSON mode and timeout
        try:
            chat_completion = await asyncio.wait_for(
                self.client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": self.SYSTEM_INSTRUCTION},
                        {"role": "user", "content": prompt},
                    ],
                    model=self.model_name,
                    temperature=0.3,
                    max_tokens=1500,
                    response_format={"type": "json_object"},
                ),
                timeout=self.timeout,
            )

            raw_content = chat_completion.choices[0].message.content or "{}"
            # Clean potential markdown fences (e.g. ```json ... ```)
            clean_content = raw_content.strip()
            if clean_content.startswith("```json"):
                clean_content = clean_content[7:]
            if clean_content.startswith("```"):
                clean_content = clean_content[3:]
            if clean_content.endswith("```"):
                clean_content = clean_content[:-3]
            clean_content = clean_content.strip()

            parsed_data = json.loads(clean_content)
            rec_response = RecommendationResponse.model_validate(parsed_data)
            rec_response.is_fallback = False

            # 3. Post-Generation Integrity Verification (Zero Hallucination Guard)
            verified_recs = self._verify_integrity(rec_response.recommendations, candidates)

            if verified_recs:
                rec_response.recommendations = verified_recs
                return rec_response
            else:
                logger.warning("LLM output failed candidate integrity verification. Using fallback.")
                return FallbackRankingEngine.rank_and_explain(request, candidates, is_relaxed)

        except asyncio.TimeoutError:
            logger.warning(f"Groq request timed out after {self.timeout}s. Serving fallback.")
            return FallbackRankingEngine.rank_and_explain(request, candidates, is_relaxed)
        except Exception as exc:
            logger.warning(f"Groq inference error ({type(exc).__name__}: {exc}). Serving fallback.")
            return FallbackRankingEngine.rank_and_explain(request, candidates, is_relaxed)

    @staticmethod
    def _verify_integrity(
        recommendations: List[RestaurantRecommendation],
        candidates: List[Restaurant],
    ) -> List[RestaurantRecommendation]:
        """Ensure all recommended venues strictly belong to the input candidate pool."""
        candidate_name_map = {c.name.strip().lower(): c for c in candidates}
        verified: List[RestaurantRecommendation] = []

        for rec in recommendations:
            key = rec.restaurant_name.strip().lower()
            if key in candidate_name_map:
                matched_candidate = candidate_name_map[key]
                # Normalize official name and rating from authoritative source
                rec.restaurant_name = matched_candidate.name
                if matched_candidate.aggregate_rating:
                    rec.rating = matched_candidate.aggregate_rating
                rec.estimated_cost_for_two = matched_candidate.average_cost_for_two
                verified.append(rec)
            else:
                logger.warning(
                    f"Dropped ungrounded restaurant '{rec.restaurant_name}' not in candidate pool."
                )

        # Re-assign clean 1-based ranks
        for idx, rec in enumerate(verified, 1):
            rec.rank = idx

        return verified

    @staticmethod
    def _build_prompt(request: UserPreferenceRequest, candidates: List[Restaurant]) -> str:
        """Construct the prompt injected into the LLM."""
        # Build compact candidate representations to conserve tokens
        candidate_dicts = []
        for idx, c in enumerate(candidates, 1):
            candidate_dicts.append(
                {
                    "candidate_id": idx,
                    "name": c.name,
                    "locality": c.locality,
                    "cuisines": c.cuisines_str,
                    "average_cost_for_two": c.average_cost_for_two,
                    "budget_tier": c.budget_tier,
                    "rating": c.aggregate_rating or "Unrated",
                    "votes": c.votes,
                    "popular_dishes": c.dish_liked or "N/A",
                    "restaurant_type": c.rest_type or "N/A",
                }
            )

        candidates_json = json.dumps(candidate_dicts, indent=2)

        return (
            f"USER PREFERENCES:\n"
            f"- Location: {request.location}\n"
            f"- Budget Tier: {request.budget_tier}\n"
            f"- Preferred Cuisines: {', '.join(request.cuisines) if request.cuisines else 'Any'}\n"
            f"- Minimum Rating: {request.min_rating}\n"
            f"- Special Context / Vibes: {request.additional_preferences or 'None'}\n\n"
            f"CANDIDATE RESTAURANTS (Top {len(candidates)} pre-filtered matches):\n"
            f"{candidates_json}\n\n"
            f"TASK:\n"
            f"1. Select and rank the top 3 to 5 best matching restaurants.\n"
            f"2. Write a compelling, humanized explanation for each recommendation explaining why it fits.\n"
            f"3. Generate a concise summary synthesizing the results.\n"
            f"4. Output strictly in valid JSON format adhering to the required schema."
        )


def get_llm_service() -> LLMService:
    """Dependency helper to obtain an LLMService instance."""
    return LLMService()
