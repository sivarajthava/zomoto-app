"""Automated Pytest integration for Phase 8: Golden Persona Evaluation."""

import pytest

from app.services.data_loader import get_data_loader
from app.services.llm_service import LLMService
from app.services.recommendation_service import RecommendationOrchestrator
from tests.run_persona_eval import GOLDEN_PERSONAS, evaluate_persona


@pytest.fixture(scope="module")
def evaluator_context():
    loader = get_data_loader()
    all_names = set(loader.df["name"].unique())
    orchestrator = RecommendationOrchestrator(llm_service=LLMService(api_key=""))
    return orchestrator, all_names


class TestGoldenPersonas:
    """Verify recommendation quality and zero-hallucination across all 5 personas."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("persona", GOLDEN_PERSONAS, ids=lambda p: p["id"])
    async def test_persona_evaluation(self, persona, evaluator_context):
        orchestrator, all_names = evaluator_context
        result = await evaluate_persona(orchestrator, persona, all_names)

        assert result["passed"] is True, f"Persona {persona['id']} failed: {result['failures']}"
        assert result["groundedness"] == 100.0, f"Groundedness violated: {result['groundedness']}%"
        assert result["rec_count"] >= 1
        assert result["relevance"] >= 4.0
        assert result["latency"] < 2.0, f"Latency too high: {result['latency']}s"
