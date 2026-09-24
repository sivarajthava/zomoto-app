"""Unit and mock tests for Phase 5: Stage 2 AI Reasoning Engine."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models import (
    RecommendationResponse,
    Restaurant,
    RestaurantRecommendation,
    UserPreferenceRequest,
)
from app.services.llm_service import FallbackRankingEngine, LLMService


@pytest.fixture
def sample_candidates():
    """Fixture providing a mock list of 5 Restaurant candidate entities."""
    return [
        Restaurant(
            id="1",
            name="Toscano",
            city="Bangalore",
            locality="UB City",
            address="24, Vittal Mallya Road",
            cuisines_list=["italian", "pizza"],
            cuisines_str="Italian, Pizza",
            average_cost_for_two=1400.0,
            budget_tier="medium",
            aggregate_rating=4.6,
            votes=1250,
            dish_liked="Sourdough Pizza, Tiramisu",
        ),
        Restaurant(
            id="2",
            name="Chianti",
            city="Bangalore",
            locality="Indiranagar",
            address="12th Main Road",
            cuisines_list=["italian", "pasta"],
            cuisines_str="Italian, Pasta",
            average_cost_for_two=1500.0,
            budget_tier="medium",
            aggregate_rating=4.5,
            votes=980,
            dish_liked="Ravioli, Wine",
        ),
        Restaurant(
            id="3",
            name="Onesta",
            city="Bangalore",
            locality="Koramangala",
            address="80 Feet Road",
            cuisines_list=["pizza", "italian", "desserts"],
            cuisines_str="Pizza, Italian, Desserts",
            average_cost_for_two=800.0,
            budget_tier="medium",
            aggregate_rating=4.2,
            votes=3400,
            dish_liked="Unlimited Pizza, Chocolate Mousse",
        ),
    ]


@pytest.fixture
def sample_request():
    return UserPreferenceRequest(
        location="Bangalore",
        budget_tier="medium",
        cuisines=["Italian"],
        min_rating=4.0,
        additional_preferences="Romantic outdoor seating with wine",
    )


class TestFallbackRankingEngine:
    """Verify deterministic fallback engine behavior and metadata-driven explanations."""

    def test_fallback_generates_recommendations(self, sample_request, sample_candidates):
        resp = FallbackRankingEngine.rank_and_explain(sample_request, sample_candidates)

        assert isinstance(resp, RecommendationResponse)
        assert resp.is_fallback is True
        assert len(resp.recommendations) == 3
        assert "Toscano" in resp.recommendations[0].restaurant_name
        assert resp.recommendations[0].rank == 1
        assert "UB City" in resp.recommendations[0].explanation
        assert "1,250" in resp.recommendations[0].explanation

    def test_fallback_handles_empty_candidates(self, sample_request):
        resp = FallbackRankingEngine.rank_and_explain(sample_request, [])
        assert resp.is_fallback is True
        assert len(resp.recommendations) == 0
        assert "No matching restaurants found" in resp.summary


class TestLLMServiceIntegrityAndPrompt:
    """Verify grounded prompt building and zero-hallucination post-filtering."""

    def test_build_prompt_structure(self, sample_request, sample_candidates):
        prompt = LLMService._build_prompt(sample_request, sample_candidates)
        assert "USER PREFERENCES:" in prompt
        assert "Romantic outdoor seating with wine" in prompt
        assert "CANDIDATE RESTAURANTS" in prompt
        assert "Toscano" in prompt
        assert "Chianti" in prompt

    def test_verify_integrity_drops_hallucinations(self, sample_candidates):
        # Recommendations containing 1 valid venue and 1 hallucinated venue
        raw_recs = [
            RestaurantRecommendation(
                rank=1,
                restaurant_name="Toscano",
                cuisine="Italian",
                rating=4.6,
                estimated_cost_for_two=1400.0,
                explanation="Authentic Italian.",
            ),
            RestaurantRecommendation(
                rank=2,
                restaurant_name="Phantom Luigi Pizzeria",  # NOT in candidates
                cuisine="Italian",
                rating=5.0,
                estimated_cost_for_two=1000.0,
                explanation="Invented restaurant.",
            ),
            RestaurantRecommendation(
                rank=3,
                restaurant_name="Chianti",
                cuisine="Italian",
                rating=4.5,
                estimated_cost_for_two=1500.0,
                explanation="Great trattoria.",
            ),
        ]

        verified = LLMService._verify_integrity(raw_recs, sample_candidates)

        # Phantom Luigi should be dropped; Toscano and Chianti should remain
        assert len(verified) == 2
        assert verified[0].restaurant_name == "Toscano"
        assert verified[0].rank == 1
        assert verified[1].restaurant_name == "Chianti"
        assert verified[1].rank == 2  # Re-indexed to rank 2


class TestLLMServiceMockedInference:
    """Verify LLMService execution under mock Groq responses, errors, and timeouts."""

    @pytest.mark.asyncio
    async def test_offline_mode_without_api_key(self, sample_request, sample_candidates):
        """When no API key is provided, system automatically uses fallback."""
        service = LLMService(api_key="")
        resp = await service.rank_and_explain(sample_request, sample_candidates)

        assert resp.is_fallback is True
        assert len(resp.recommendations) > 0

    @pytest.mark.asyncio
    async def test_successful_groq_inference(self, sample_request, sample_candidates):
        """Verify successful Groq structured JSON generation."""
        mock_choice = MagicMock()
        mock_choice.message.content = json.dumps(
            {
                "summary": "Curated the best romantic Italian spots in Bangalore for you.",
                "is_fallback": False,
                "recommendations": [
                    {
                        "rank": 1,
                        "restaurant_name": "Toscano",
                        "cuisine": "Italian, Pizza",
                        "rating": 4.6,
                        "estimated_cost_for_two": 1400.0,
                        "explanation": "Ideal for a romantic date with wine and sourdough pizza.",
                    },
                    {
                        "rank": 2,
                        "restaurant_name": "Chianti",
                        "cuisine": "Italian, Pasta",
                        "rating": 4.5,
                        "estimated_cost_for_two": 1500.0,
                        "explanation": "Cozy candle-lit trattoria ambience with handmade pasta.",
                    },
                ],
            }
        )
        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]

        service = LLMService(api_key="mock_test_key")
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
        service.client = mock_client

        resp = await service.rank_and_explain(sample_request, sample_candidates)

        assert resp.is_fallback is False
        assert len(resp.recommendations) == 2
        assert resp.recommendations[0].restaurant_name == "Toscano"
        assert "romantic date" in resp.recommendations[0].explanation

    @pytest.mark.asyncio
    async def test_groq_timeout_triggers_fallback(self, sample_request, sample_candidates):
        """Verify that an API timeout gracefully returns fallback results."""
        import asyncio

        service = LLMService(api_key="mock_test_key", timeout=0.01)

        async def slow_call(*args, **kwargs):
            await asyncio.sleep(0.1)
            return MagicMock()

        mock_client = MagicMock()
        mock_client.chat.completions.create = slow_call
        service.client = mock_client

        resp = await service.rank_and_explain(sample_request, sample_candidates)

        assert resp.is_fallback is True
        assert len(resp.recommendations) > 0

    @pytest.mark.asyncio
    async def test_groq_api_exception_triggers_fallback(self, sample_request, sample_candidates):
        """Verify that an API exception (e.g. 429 quota) gracefully returns fallback results."""
        service = LLMService(api_key="mock_test_key")
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=RuntimeError("429 Rate Limit Exceeded"))
        service.client = mock_client

        resp = await service.rank_and_explain(sample_request, sample_candidates)

        assert resp.is_fallback is True
        assert len(resp.recommendations) > 0

