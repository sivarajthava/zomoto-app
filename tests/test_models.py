"""Unit tests for Phase 3 domain models and application configuration."""

import pytest
from pydantic import ValidationError

from app.config import Settings, settings
from app.models import (
    MetadataResponse,
    RecommendationResponse,
    Restaurant,
    RestaurantRecommendation,
    UserPreferenceRequest,
)


class TestUserPreferenceRequest:
    """Test validation and boundary conditions for UserPreferenceRequest."""

    def test_valid_minimal_request(self):
        req = UserPreferenceRequest(location="Bangalore")
        assert req.location == "Bangalore"
        assert req.budget_tier == "medium"
        assert req.min_rating == 3.5
        assert req.cuisines == []
        assert req.additional_preferences is None

    def test_valid_full_request(self):
        req = UserPreferenceRequest(
            location=" Koramangala ",
            budget_tier="LOW",
            cuisines=["North Indian", "Mughlai"],
            min_rating=4.2,
            additional_preferences="Romantic outdoor seating with live music",
        )
        assert req.location == "Koramangala"
        assert req.budget_tier == "low"
        assert req.min_rating == 4.2
        assert req.cuisines == ["North Indian", "Mughlai"]
        assert req.additional_preferences == "Romantic outdoor seating with live music"

    @pytest.mark.parametrize("tier", ["low", "medium", "high", "LOW", " Medium ", "HIGH"])
    def test_budget_tier_normalization(self, tier):
        req = UserPreferenceRequest(location="Delhi", budget_tier=tier)
        assert req.budget_tier in {"low", "medium", "high"}

    @pytest.mark.parametrize("invalid_tier", ["ultra_low", "cheap", "expensive", "", "123"])
    def test_invalid_budget_tier_raises(self, invalid_tier):
        with pytest.raises(ValidationError) as exc:
            UserPreferenceRequest(location="Delhi", budget_tier=invalid_tier)
        assert "budget_tier" in str(exc.value)

    @pytest.mark.parametrize("empty_loc", ["", "   ", None])
    def test_empty_location_raises(self, empty_loc):
        with pytest.raises(ValidationError):
            UserPreferenceRequest(location=empty_loc)

    @pytest.mark.parametrize("rating", [0.0, 1.0, 3.5, 4.8, 5.0])
    def test_valid_rating_boundaries(self, rating):
        req = UserPreferenceRequest(location="Bangalore", min_rating=rating)
        assert req.min_rating == rating

    @pytest.mark.parametrize("invalid_rating", [-0.1, -1.0, 5.1, 10.0])
    def test_invalid_rating_boundaries(self, invalid_rating):
        with pytest.raises(ValidationError) as exc:
            UserPreferenceRequest(location="Bangalore", min_rating=invalid_rating)
        assert "min_rating" in str(exc.value)

    def test_preferences_max_length(self):
        # 300 chars should pass
        valid_text = "a" * 300
        req = UserPreferenceRequest(location="Bangalore", additional_preferences=valid_text)
        assert req.additional_preferences == valid_text

        # 301 chars should raise ValidationError
        with pytest.raises(ValidationError) as exc:
            UserPreferenceRequest(location="Bangalore", additional_preferences="a" * 301)
        assert "additional_preferences" in str(exc.value)


class TestRecommendationResponseModels:
    """Test recommendation item and response serialization."""

    def test_restaurant_recommendation_model(self):
        rec = RestaurantRecommendation(
            rank=1,
            restaurant_name="Toscano",
            cuisine="Italian, Wine",
            rating=4.5,
            estimated_cost_for_two=1400.0,
            explanation="Charming outdoor patio with authentic sourdough pizza.",
        )
        assert rec.rank == 1
        assert rec.restaurant_name == "Toscano"
        assert rec.rating == 4.5

    def test_recommendation_response_model(self):
        rec = RestaurantRecommendation(
            rank=1,
            restaurant_name="Chianti",
            cuisine="Italian",
            rating=4.6,
            estimated_cost_for_two=1500.0,
            explanation="Great pasta and cozy wine bar vibe.",
        )
        resp = RecommendationResponse(
            summary="Top romantic Italian spot found.",
            is_fallback=False,
            recommendations=[rec],
        )
        assert len(resp.recommendations) == 1
        assert resp.is_fallback is False
        assert "Chianti" in resp.recommendations[0].restaurant_name

    def test_metadata_response_model(self):
        meta = MetadataResponse(
            total_restaurants=100,
            cities=["Bangalore"],
            localities=["Indiranagar", "Koramangala"],
            cuisines=["Italian", "North Indian"],
            budget_tiers=["low", "medium", "high"],
        )
        assert meta.total_restaurants == 100
        assert len(meta.cities) == 1


class TestApplicationSettings:
    """Test application settings defaults and path resolutions."""

    def test_default_settings(self):
        s = Settings()
        assert s.default_llm_model == "openai/gpt-oss-120b"
        assert hasattr(s, "groq_api_key")
        assert s.max_candidates_stage_1 == 15
        assert s.min_candidates_threshold == 5
        assert s.request_timeout_seconds == 4.0
        assert s.absolute_data_path.name == "zomato_clean.parquet"
