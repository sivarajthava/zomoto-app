"""Unit tests for Phase 7: Streamlit UI components and hybrid caller."""

import pytest

from app.models import RecommendationResponse, UserPreferenceRequest
from app.ui.streamlit_app import get_recommendations_hybrid, load_metadata_cached


class TestStreamlitHelpers:
    """Verify Streamlit helper functions and hybrid execution pipeline."""

    def test_load_metadata_cached(self):
        metadata = load_metadata_cached()
        assert metadata.total_restaurants >= 8000
        assert "Bangalore" in metadata.cities
        assert len(metadata.localities) > 20
        assert len(metadata.cuisines) > 10

    def test_get_recommendations_hybrid_execution(self):
        req = UserPreferenceRequest(
            location="Indiranagar",
            budget_tier="medium",
            cuisines=["Italian"],
            min_rating=4.0,
            additional_preferences="Cozy dinner with wine",
        )
        response = get_recommendations_hybrid(req)

        assert isinstance(response, RecommendationResponse)
        assert len(response.recommendations) > 0
        assert len(response.recommendations) <= 5

        first = response.recommendations[0]
        assert first.rank == 1
        assert len(first.restaurant_name) > 0
        assert first.rating >= 4.0
        assert len(first.explanation) > 15
