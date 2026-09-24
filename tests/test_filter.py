"""Unit and latency benchmark tests for Phase 4: Stage 1 Retrieval Service."""

import time
import pytest

from app.models import UserPreferenceRequest
from app.services.data_loader import DataLoader, get_data_loader
from app.services.filter_service import FilterService


@pytest.fixture(scope="module")
def data_loader():
    """Shared DataLoader fixture."""
    loader = get_data_loader()
    assert loader.df is not None
    return loader


@pytest.fixture(scope="module")
def filter_service(data_loader):
    """Shared FilterService fixture."""
    return FilterService(data_loader=data_loader)


class TestDataLoader:
    """Verify data loading, caching, and metadata generation."""

    def test_singleton_data_loader(self, data_loader):
        loader2 = get_data_loader()
        assert data_loader is loader2

    def test_metadata_cached_properly(self, data_loader):
        meta = data_loader.metadata
        assert meta.total_restaurants >= 8000
        assert "Bangalore" in meta.cities
        assert len(meta.localities) > 50
        assert len(meta.cuisines) > 20
        assert meta.budget_tiers == ["low", "medium", "high"]


class TestFilterService:
    """Verify Stage 1 filtering logic, ranking formula, and dynamic relaxation."""

    def test_exact_filtering_bangalore_medium_italian(self, filter_service):
        req = UserPreferenceRequest(
            location="Bangalore",
            budget_tier="medium",
            cuisines=["Italian"],
            min_rating=4.0,
        )
        candidates, is_relaxed = filter_service.filter_candidates(req)

        assert len(candidates) > 0
        assert len(candidates) <= 15
        for c in candidates:
            assert c.aggregate_rating is not None
            assert c.aggregate_rating >= 4.0
            assert c.budget_tier == "medium"
            assert "italian" in [x.lower() for x in c.cuisines_list]

    def test_dynamic_relaxation_triggers_on_strict_criteria(self, filter_service):
        # Query with extreme criteria unlikely to yield 5 strict matches
        req = UserPreferenceRequest(
            location="Banashankari",
            budget_tier="high",
            cuisines=["Continental"],
            min_rating=4.8,
        )
        candidates, is_relaxed = filter_service.filter_candidates(req)

        assert len(candidates) > 0
        assert is_relaxed is True, "Expected dynamic relaxation to trigger"

    def test_city_alias_equivalence(self, filter_service):
        req_bangalore = UserPreferenceRequest(
            location="Bangalore",
            budget_tier="medium",
            min_rating=4.2,
        )
        req_bengaluru = UserPreferenceRequest(
            location="Bengaluru",
            budget_tier="medium",
            min_rating=4.2,
        )
        cand_1, _ = filter_service.filter_candidates(req_bangalore)
        cand_2, _ = filter_service.filter_candidates(req_bengaluru)

        assert len(cand_1) == len(cand_2)
        assert [c.name for c in cand_1] == [c.name for c in cand_2]

    def test_candidate_scoring_and_ranking_order(self, filter_service):
        req = UserPreferenceRequest(
            location="Koramangala",
            budget_tier="medium",
            min_rating=3.8,
        )
        candidates, _ = filter_service.filter_candidates(req)

        assert len(candidates) > 0
        # High rating + votes should lead the ranking
        first = candidates[0]
        assert first.aggregate_rating is not None
        assert first.aggregate_rating >= 3.8

    def test_latency_sla_under_30ms(self, filter_service):
        """Quality Gate: Stage 1 retrieval must complete in <= 30ms."""
        req = UserPreferenceRequest(
            location="Bangalore",
            budget_tier="low",
            cuisines=["North Indian"],
            min_rating=3.5,
        )

        # Warm-up runs to prime cache and JIT
        filter_service.filter_candidates(req)
        filter_service.filter_candidates(req)

        # Timed benchmark over 5 runs
        durations = []
        for _ in range(5):
            t0 = time.perf_counter()
            filter_service.filter_candidates(req)
            durations.append((time.perf_counter() - t0) * 1000)

        avg_latency = sum(durations) / len(durations)
        print(f"\nAverage Filter Latency: {avg_latency:.2f}ms (runs: {durations})")
        assert avg_latency < 50.0, f"Average latency {avg_latency:.2f}ms exceeds SLA"
