# Project Plan: AI-Powered Restaurant Recommendation System (Zomato Use Case)
*(Python Implementation Architecture)*

---

## 1. Executive Summary & Objectives

### 1.1 Overview
This project implements an **AI-Powered Restaurant Recommendation System** modeled after Zomato's discovery platform, built entirely in **Python**. By combining structured tabular datasets with Groq's ultra-low latency LPU Inference Engine (running open-weights models like `openai/gpt-oss-120b` via the official `groq` SDK and Antigravity orchestration), the system replaces rigid categorical filters with nuanced, personalized, conversational dining recommendations at lightning speed.

### 1.2 Core Objectives
- **Context-Aware Recommendations**: Interpret complex user queries and unspoken intent (e.g., *"quiet anniversary dinner under ₹1500 with Italian food and outdoor seating"*).
- **Two-Stage Hybrid Retrieval**:
  - **Stage 1 (Deterministic Filter)**: High-speed heuristic pre-filtering using Python (`pandas` / `SQLite` / in-memory indexing) on location, budget tier, cuisine, and rating.
  - **Stage 2 (Semantic Re-ranking & Synthesis)**: Context-rich LLM prompting and ranking with structured JSON output and personalized reasoning.
- **Explainable AI (XAI)**: Generate human-like justifications explaining *why* each restaurant specifically meets the user's criteria.
- **Modern Python Stack**: Clean, production-ready architecture using **FastAPI** (REST API & OpenAPI documentation), **Pydantic v2** (schema validation), **Streamlit** (interactive user discovery UI), and the high-speed **`groq` Python SDK**.

---

## 2. System Architecture & High-Level Design

```
+---------------------------------------------------------------------------------+
|                                 User Interface                                  |
|            Streamlit Web App  /  FastAPI Interactive Swagger Docs (OpenAPI)      |
+---------------------------------------------------------------------------------+
                                       |
                                       v [HTTP / Internal Call with UserPreferences]
+---------------------------------------------------------------------------------+
|                          Python Application Layer (FastAPI)                     |
|                                                                                 |
|  +---------------------------------------------------------------------------+  |
|  | Request Validation & Ingestion (Pydantic v2)                              |  |
|  |  - Location, Budget Tier, Cuisines, Min Rating, Natural Text Preferences   |  |
|  +---------------------------------------------------------------------------+  |
|                                       |                                         |
|                                       v                                         |
|  +---------------------------------------------------------------------------+  |
|  | Stage 1: Deterministic Filtering & Retrieval (FilterService)              |  |
|  |  - In-memory DataFrame / SQLite candidate search                          |  |
|  |  - Exact & fuzzy location matching                                        |  |
|  |  - Hard constraint checks: rating >= min_rating, budget tier alignment    |  |
|  |  - Candidate pool extraction (Top 10-20 candidates based on score & votes) |  |
|  +---------------------------------------------------------------------------+  |
|                                       |                                         |
|                                       v                                         |
|  +---------------------------------------------------------------------------+  |
|  | Stage 2: Recommendation & Reasoning Engine (LLMService)                   |  |
|  |  - Grounded Prompt Builder (Candidate context + User constraints)         |  |
|  |  - Groq LPU (openai/gpt-oss-120b via groq SDK)                            |  |
|  |  - Structured Output Parsing (Pydantic schema enforcement)                 |  |
|  |  - Fallback deterministic ranking if LLM offline / rate-limited          |  |
|  +---------------------------------------------------------------------------+  |
|                                       |                                         |
+---------------------------------------------------------------------------------+
           |                                                   |
           v                                                   v
+-------------------------------------+       +-----------------------------------+
|      Data Store & Ingestion         |       |        LLM / AI Platform          |
|  - Preprocessed Zomato Dataset      |       |  - Groq Cloud API                 |
|    (Hugging Face Ingestion via      |       |    (openai/gpt-oss-120b)          |
|     Pandas / Parquet / SQLite)      |       |  - Structured JSON Output Schema  |
+-------------------------------------+       +-----------------------------------+
```

---

## 3. End-to-End Workflow Breakdown

### Phase 1: Data Ingestion & Preprocessing Pipeline
* **Source**: Hugging Face Dataset – [`ManikaSaini/zomato-restaurant-recommendation`](https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation)
* **Ingestion Script** (`scripts/ingest_data.py`):
  1. Download dataset via `datasets` library or direct HTTP CSV download.
  2. Normalize and clean columns:
     - `restaurant_name`: Cleaned string.
     - `city` / `locality`: Standardized casing, whitespace trimmed.
     - `cuisines`: Parsed into a clean list of lowercase/title-cased strings (e.g., `["North Indian", "Mughlai"]`).
     - `average_cost_for_two`: Converted to numeric float/int, handling missing/invalid records.
     - `aggregate_rating`: Converted to float (0.0 to 5.0), replacing `"NEW"` or `"-"` with `None` / median imputation.
     - `votes`: Numeric integer count.
     - `highlights`: Parsed into tags (e.g., `["Outdoor Seating", "Live Music", "Valet Parking"]`).
  3. **Derived Feature - Budget Tier**:
     - **Low**: Cost for two $\le 500$
     - **Medium**: Cost for two $> 500$ and $\le 1500$
     - **High / Fine Dining**: Cost for two $> 1500$
  4. Serialize clean data to `data/processed_restaurants.parquet` or an embedded SQLite database (`data/zomato.db`) for sub-millisecond retrieval.

### Phase 2: User Preference Capture
Users supply structured criteria alongside contextual, natural language requests:
- **Location**: City or locality (e.g., *"Bangalore"*, *"Indiranagar"*, *"Connaught Place, New Delhi"*).
- **Budget**: Categorical (`"low"`, `"medium"`, `"high"`) or optional numerical budget limit.
- **Cuisine**: List of desired cuisines (e.g., `["Italian", "Pizza"]`, `["North Indian"]`).
- **Minimum Rating**: Minimum threshold (e.g., $\ge 3.8$ or $\ge 4.0$).
- **Contextual / Ambient Preferences**: Free-text nuances (e.g., *"romantic anniversary rooftop with quiet ambiance"*, *"quick lunch near office with high hygiene"*).

### Phase 3: Integration Layer (Pre-Filtering & Candidate Pruning)
Passing the entire dataset to an LLM is inefficient, slow, and expensive. The integration layer performs a deterministic funnel:
1. **Filtering**:
   - Filter records where `city.str.contains(user_location, case=False)`.
   - Filter `aggregate_rating >= min_rating`.
   - Filter `budget_tier == user_budget` (with automatic fallback to adjacent tier if $< 5$ matches).
   - Match cuisine overlap against restaurant cuisine list.
2. **Scoring & Candidate Selection**:
   - Calculate heuristic ranking score: $\text{Score} = (\text{Rating} \times 0.6) + (\log_{10}(\text{Votes} + 1) \times 0.4)$.
   - Extract top 10–20 best candidate restaurants.
   - Format candidates into a compact JSON context block for the LLM.

### Phase 4: Recommendation Engine (LLM Reasoning & Ranking)
1. **Prompt Engineering & Grounding**:
   - **Role**: World-class culinary curator and local food critic.
   - **Grounding Rule**: Strict zero-hallucination constraint—the LLM is strictly forbidden from recommending any restaurant not present in the supplied candidate list.
   - **Reasoning**: Match the user's explicit criteria *and* implicit nuances (ambiance, occasion, speed) against candidate highlights, cuisines, and price points.
2. **Structured JSON Output**:
   Enforced via Pydantic schema and Groq's native JSON mode (`response_format={"type": "json_object"}`):
   ```json
   {
     "summary": "Here are the top 3 spots in Bangalore matching your romantic Italian dinner request...",
     "recommendations": [
       {
         "rank": 1,
         "restaurant_name": "Toscano",
         "cuisine": "Italian, Pizza, Wine",
         "rating": 4.6,
         "estimated_cost_for_two": 1400,
         "explanation": "Perfect for a romantic date with intimate outdoor seating, stellar wood-fired pizzas, and fits comfortably within your medium budget."
       }
     ]
   }
   ```

### Phase 5: Output Display & Presentation
- **FastAPI Endpoint**: `POST /api/v1/recommendations` returning validated JSON.
- **Streamlit Web UI**:
  - Interactive sidebar for location, budget tier, cuisine multi-select, and rating slider.
  - Natural language prompt input box.
  - Visually engaging recommendation cards displaying:
    - Restaurant name & star rating badge
    - Cuisine tags & estimated cost for two
    - AI-generated contextual justification
    - Summary banner highlighting trade-offs

---

## 4. Python Technology Stack

| Component | Library / Tool | Purpose & Justification |
|---|---|---|
| **Programming Language** | **Python 3.11+ (Tested on 3.14)** | Native ecosystem for data processing, AI libraries, and rapid prototyping. |
| **API Backend** | **FastAPI + Uvicorn** | High performance, async support, automated OpenAPI / Swagger docs, native Pydantic validation. |
| **Data Validation** | **Pydantic v2** | Strict type checking, auto-serialization, and Groq structured output schemas. |
| **Data Ingestion & Storage** | **Pandas / Parquet / DuckDB or SQLite** | Fast vector operations, columnar storage, instantaneous filtering over 100k+ rows. |
| **AI / LLM Integration** | **groq SDK** | Official Groq Python SDK for ultra-fast LPU inference using `openai/gpt-oss-120b` with native JSON mode. |
| **Interactive UI** | **Streamlit** | Rapid frontend development, reactive state, intuitive sliders, cards, and markdown rendering. |
| **Testing** | **pytest + pytest-asyncio + httpx** | Automated unit, filtering, and API test coverage. |
| **Environment & Package Mgmt** | **venv + pip** | Isolated virtual environment adhering to project standards. |

---

## 5. Domain Models & Pydantic Schemas

### 5.1 Models (`app/models.py`)
```python
from typing import List, Optional
from pydantic import BaseModel, Field

class Restaurant(BaseModel):
    id: str
    name: str
    city: str
    locality: str
    cuisines: List[str]
    average_cost_for_two: float
    budget_tier: str  # "low", "medium", "high"
    aggregate_rating: float
    votes: int
    highlights: List[str] = Field(default_factory=list)

class UserPreferenceRequest(BaseModel):
    location: str = Field(..., description="Target city or area, e.g. Bangalore, Delhi")
    budget_tier: str = Field(..., description="low, medium, or high")
    cuisines: List[str] = Field(default_factory=list, description="Preferred cuisines")
    min_rating: float = Field(3.5, ge=0.0, le=5.0, description="Minimum acceptable rating")
    additional_preferences: Optional[str] = Field(
        None, description="Free-text preferences like 'romantic rooftop', 'quick service', 'family friendly'"
    )

class RestaurantRecommendation(BaseModel):
    rank: int
    restaurant_name: str
    cuisine: str
    rating: float
    estimated_cost_for_two: float
    explanation: str

class RecommendationResponse(BaseModel):
    summary: str
    recommendations: List[RestaurantRecommendation]
```

---

## 6. Project Directory Structure

```
DemoZomoto/
│
├── .venv/                         # Python virtual environment (ignored in git)
├── data/
│   ├── raw/                       # Downloaded raw Hugging Face dataset files
│   └── processed/
│       └── zomato_clean.parquet   # Preprocessed fast-loading dataset
│
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application entrypoint
│   ├── config.py                  # App configuration & Groq API keys
│   ├── models.py                  # Pydantic request/response schemas
│   ├── services/
│   │   ├── __init__.py
│   │   ├── data_loader.py         # Loads & indexes processed restaurant data
│   │   ├── filter_service.py      # Stage 1 deterministic filtering logic
│   │   └── llm_service.py         # Stage 2 Groq prompt & structured output
│   └── ui/
│       └── streamlit_app.py       # Streamlit interactive frontend
│
├── scripts/
│   └── ingest_data.py             # Hugging Face dataset download & cleaning script
│
├── tests/
│   ├── test_filter.py             # Unit tests for Stage 1 filtering logic
│   ├── test_llm_service.py        # Mocked tests for LLM prompt & parsing
│   └── test_api.py                # FastAPI endpoint integration tests
│
├── problemStatement.txt           # Project problem statement
├── zomoto-plan.md                 # Master project blueprint
├── requirements.txt               # Managed Python dependencies
└── README.md                      # Project setup & execution guide
```

---

## 7. Implementation Milestones & Roadmap

```
+-------------------------------------------------------------------------------+
| Milestone 1: Environment Setup & Data Ingestion Pipeline                     |
| - Initialize .venv and install base dependencies                              |
| - Download ManikaSaini/zomato-restaurant-recommendation from Hugging Face     |
| - Clean, normalize cuisines/ratings/costs, compute budget tiers               |
| - Save to data/processed/zomato_clean.parquet                                 |
+-------------------------------------------------------------------------------+
                                       |
                                       v
+-------------------------------------------------------------------------------+
| Milestone 2: Core Domain Logic & Stage 1 Filter Service                       |
| - Build Pydantic models (Restaurant, UserPreferenceRequest, etc.)             |
| - Implement FilterService for fast in-memory candidate retrieval              |
| - Add fallback relaxation logic when zero/few matches found                   |
| - Verify with unit tests (test_filter.py)                                     |
+-------------------------------------------------------------------------------+
                                       |
                                       v
+-------------------------------------------------------------------------------+
| Milestone 3: LLM Reasoning Engine & Grounded Prompting                        |
| - Configure groq client with openai/gpt-oss-120b                              |
| - Construct grounded prompt strictly bound to Stage 1 candidates              |
| - Enforce JSON mode (response_format={'type': 'json_object'}) & Pydantic      |
| - Implement graceful fallback if LLM is unavailable or rate-limited           |
+-------------------------------------------------------------------------------+
                                       |
                                       v
+-------------------------------------------------------------------------------+
| Milestone 4: FastAPI REST Service                                             |
| - Expose POST /api/v1/recommendations endpoint                                |
| - Wire FilterService + LLMService into unified orchestrator                   |
| - Add automated Swagger UI documentation and health check endpoint            |
| - Verify with test_api.py                                                     |
+-------------------------------------------------------------------------------+
                                       |
                                       v
+-------------------------------------------------------------------------------+
| Milestone 5: Streamlit Interactive UI & Polishing                             |
| - Build responsive web UI with location, budget, cuisine, rating sliders      |
| - Add conversational preference input and recommendation result cards         |
| - End-to-end verification across real-world dining scenarios                  |
+-------------------------------------------------------------------------------+
```

---

## 8. Safeguards, Resilience & Edge Cases

1. **Zero Candidates Found**:
   - If user constraints (e.g. strict location + niche cuisine) yield zero matches, the `FilterService` broadens the search (e.g. relax rating by 0.5, or include adjacent budget tiers) and alerts the user transparently.
2. **Hallucination Prevention**:
   - The LLM prompt explicitly restricts recommendations to the exact subset of candidate IDs and names passed in the prompt context. Unlisted restaurants are never generated.
3. **Structured Output Resilience**:
   - Using Groq's native `response_format={"type": "json_object"}` alongside Pydantic schema validation (`RecommendationResponse.model_validate`) guarantees valid JSON adhering to our model.
4. **Offline / Fallback Mode**:
   - If the LLM API quota is exceeded or network fails, the system automatically falls back to deterministic heuristic ranking (weighted rating + votes) with template-based explanations, ensuring high availability.

---

## 9. Definition of Done (DoD)
- [ ] Python virtual environment configured with clean `requirements.txt`.
- [ ] Dataset ingestion script downloads and cleans Hugging Face Zomato records.
- [ ] `FilterService` filters candidates under 50ms.
- [ ] `LLMService` produces structured recommendations with tailored explanations via Groq.
- [ ] FastAPI endpoint `/api/v1/recommendations` operational and documented via OpenAPI.
- [ ] Streamlit interface provides an intuitive user discovery experience.
- [ ] Full test suite passing with `pytest`.
