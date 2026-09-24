"""Integration tests for Phase 6: FastAPI REST Gateway and Endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
def client_transport():
    return ASGITransport(app=app)


class TestApiEndpoints:
    """Verify status codes, response payloads, and headers across all API routes."""

    @pytest.mark.asyncio
    async def test_root_endpoint(self, client_transport):
        async with AsyncClient(transport=client_transport, base_url="http://test") as ac:
            res = await ac.get("/")
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "online"
            assert "X-Process-Time" in res.headers

    @pytest.mark.asyncio
    async def test_root_endpoint_html_browser(self, client_transport):
        async with AsyncClient(transport=client_transport, base_url="http://test") as ac:
            res = await ac.get("/", headers={"accept": "text/html,application/xhtml+xml"})
            assert res.status_code == 200
            assert "text/html" in res.headers.get("content-type", "")
            assert "DineMind" in res.text or "zomato" in res.text

    @pytest.mark.asyncio
    async def test_app_endpoint_html(self, client_transport):
        async with AsyncClient(transport=client_transport, base_url="http://test") as ac:
            res = await ac.get("/app")
            assert res.status_code == 200
            assert "text/html" in res.headers.get("content-type", "")
            assert "DineMind" in res.text or "zomato" in res.text

    @pytest.mark.asyncio
    async def test_health_check_endpoint(self, client_transport):
        async with AsyncClient(transport=client_transport, base_url="http://test") as ac:
            res = await ac.get("/health")
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "healthy"
            assert data["records_loaded"] >= 8000

    @pytest.mark.asyncio
    async def test_metadata_endpoint(self, client_transport):
        async with AsyncClient(transport=client_transport, base_url="http://test") as ac:
            res = await ac.get("/api/v1/metadata")
            assert res.status_code == 200
            data = res.json()
            assert "cities" in data
            assert "Bangalore" in data["cities"]
            assert len(data["localities"]) > 20
            assert len(data["cuisines"]) > 10
            assert data["budget_tiers"] == ["low", "medium", "high"]

    @pytest.mark.asyncio
    async def test_shorthand_routes_meta_and_recommend(self, client_transport):
        async with AsyncClient(transport=client_transport, base_url="http://test") as ac:
            meta_res = await ac.get("/api/meta")
            assert meta_res.status_code == 200
            assert "cities" in meta_res.json()

            payload = {
                "location": "Bangalore",
                "budget_tier": "low",
                "min_rating": 3.8,
            }
            rec_res = await ac.post("/api/recommend", json=payload)
            assert rec_res.status_code == 200
            assert "recommendations" in rec_res.json()

    @pytest.mark.asyncio
    async def test_post_recommendations_success(self, client_transport):
        payload = {
            "location": "Bangalore",
            "budget_tier": "medium",
            "cuisines": ["Italian"],
            "min_rating": 4.0,
            "additional_preferences": "Romantic rooftop dinner with wine",
        }
        async with AsyncClient(transport=client_transport, base_url="http://test") as ac:
            res = await ac.post("/api/v1/recommendations", json=payload)
            assert res.status_code == 200
            data = res.json()
            assert "summary" in data
            assert "recommendations" in data
            assert len(data["recommendations"]) > 0
            # Verify structure of first item
            first = data["recommendations"][0]
            assert first["rank"] == 1
            assert "restaurant_name" in first
            assert "explanation" in first
            assert len(first["explanation"]) > 10

    @pytest.mark.asyncio
    async def test_post_recommendations_validation_failure_rating(self, client_transport):
        payload = {
            "location": "Bangalore",
            "budget_tier": "medium",
            "min_rating": 6.5,  # Invalid rating > 5.0
        }
        async with AsyncClient(transport=client_transport, base_url="http://test") as ac:
            res = await ac.post("/api/v1/recommendations", json=payload)
            assert res.status_code == 422
            data = res.json()
            assert "errors" in data

    @pytest.mark.asyncio
    async def test_post_recommendations_validation_failure_budget(self, client_transport):
        payload = {
            "location": "Bangalore",
            "budget_tier": "ultra_cheap",  # Invalid tier
        }
        async with AsyncClient(transport=client_transport, base_url="http://test") as ac:
            res = await ac.post("/api/v1/recommendations", json=payload)
            assert res.status_code == 422

    @pytest.mark.asyncio
    async def test_post_recommendations_validation_failure_missing_location(self, client_transport):
        payload = {
            "budget_tier": "medium",
        }
        async with AsyncClient(transport=client_transport, base_url="http://test") as ac:
            res = await ac.post("/api/v1/recommendations", json=payload)
            assert res.status_code == 422

    @pytest.mark.asyncio
    async def test_metadata_budget_bands(self, client_transport):
        async with AsyncClient(transport=client_transport, base_url="http://test") as ac:
            res = await ac.get("/api/v1/metadata")
            assert res.status_code == 200
            data = res.json()
            assert "budget_bands" in data
            assert len(data["budget_bands"]) >= 3
            first_band = data["budget_bands"][0]
            assert "id" in first_band
            assert "label" in first_band

    @pytest.mark.asyncio
    async def test_nosh_frontend_payload_and_response_compatibility(self, client_transport):
        """Verify nosh-frontend payload format (locality, budget, cuisine, extras) and response fields."""
        payload = {
            "locality": "Koramangala",
            "budget": "medium",
            "cuisine": "Italian",
            "min_rating": 3.8,
            "extras": "quiet dinner with good wine",
        }
        async with AsyncClient(transport=client_transport, base_url="http://test") as ac:
            res = await ac.post("/api/v1/recommendations", json=payload)
            assert res.status_code == 200
            data = res.json()
            assert "summary" in data
            assert "candidate_count" in data
            assert data["candidate_count"] > 0
            assert "llm_used" in data
            assert "recommendations" in data
            assert len(data["recommendations"]) > 0

            # Verify card fields expected by frontend/src/main.js
            card = data["recommendations"][0]
            assert "rank" in card
            assert "name" in card
            assert "restaurant_name" in card
            assert card["name"] == card["restaurant_name"]
            assert "rating" in card
            assert "votes" in card
            assert "estimated_cost" in card
            assert "estimated_cost_for_two" in card
            assert card["estimated_cost"] == card["estimated_cost_for_two"]
            assert "locality" in card
            assert "rest_types" in card
            assert "book_table" in card
            assert "online_order" in card
            assert "cuisines" in card
            assert "explanation" in card

    @pytest.mark.asyncio
    async def test_relaxed_results_on_unknown_location(self, client_transport):
        """Verify unknown location triggers dynamic relaxation with message and candidate count."""
        payload = {
            "locality": "UnknownArea9999",
            "budget": "high",
        }
        async with AsyncClient(transport=client_transport, base_url="http://test") as ac:
            res = await ac.post("/api/v1/recommendations", json=payload)
            assert res.status_code == 200
            data = res.json()
            assert data["candidate_count"] > 0
            assert data["relaxed_criteria"] is True
            assert "message" in data
            assert len(data["recommendations"]) > 0

    @pytest.mark.asyncio
    async def test_all_route_aliases(self, client_transport):
        """Verify all metadata and recommendation route aliases return 200."""
        async with AsyncClient(transport=client_transport, base_url="http://test") as ac:
            for route in ["/api/meta", "/api/v1/meta", "/api/v1/metadata"]:
                res = await ac.get(route)
                assert res.status_code == 200, f"Route {route} failed with {res.status_code}"

            payload = {"locality": "Indiranagar", "budget": "low"}
            for route in ["/api/recommend", "/api/v1/recommend", "/api/v1/recommendations"]:
                res = await ac.post(route, json=payload)
                assert res.status_code == 200, f"Route {route} failed with {res.status_code}"

