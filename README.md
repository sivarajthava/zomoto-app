# 🍽️ AI-Powered Restaurant Recommendation System (Zomato Use Case)

A production-grade, two-stage restaurant recommendation service inspired by Zomato. The system bridges 12,499 real-world restaurant records with Groq's ultra-fast LPU AI reasoning (`groq` SDK) to deliver personalized, grounded dining suggestions with explainable human-like justifications.

---

## 🚀 Key Features

- **Hybrid Two-Stage Recommendation Architecture**:
  - **Stage 1 (Sub-25ms Deterministic Retrieval)**: Vectorized in-memory filtering across location, budget tier, star rating, and cuisine tokens with multi-tier dynamic query relaxation.
  - **Stage 2 (AI Reasoning Engine)**: Grounded prompt injection into Groq (`openai/gpt-oss-120b`) with strict zero-hallucination validation and structured JSON output.
- **Explainable AI (XAI)**: Generates humanized explanations detailing why each recommendation specifically satisfies the user's explicit criteria and context nuances (ambiance, occasion, speed).
- **Graceful Circuit Breaker**: Automatically serves heuristic metadata-driven recommendations when the Groq API is offline, rate-limited, or in local development.
- **Dual Presentation**:
  - **FastAPI REST API**: Async API gateway with automated OpenAPI / Swagger documentation (`/docs`).
  - **Streamlit Web UI**: Interactive web interface with real-time sliders, cuisine tags, quick inspiration presets, and recommendation cards.

---

## 📁 Repository Structure

```
DemoZomoto/
├── app/
│   ├── config.py                       # Pydantic Settings & environment variables
│   ├── models.py                       # Pydantic request/response schemas
│   ├── main.py                         # FastAPI application entrypoint
│   ├── services/
│   │   ├── data_loader.py              # In-memory Parquet dataset loader & indexer
│   │   ├── filter_service.py           # Stage 1 deterministic filtering & scoring
│   │   ├── llm_service.py              # Stage 2 Groq prompt engine & fallback
│   │   └── recommendation_service.py   # Orchestrator linking Stage 1 and Stage 2
│   └── ui/
│       └── streamlit_app.py            # Streamlit interactive web interface
│
├── data/
│   ├── raw/                            # Raw dataset snapshots
│   └── processed/
│       └── zomato_clean.parquet        # 12,499 cleaned & normalized restaurants
│
├── scripts/
│   └── ingest_data.py                  # Hugging Face data ingestion & preprocessing
│
├── tests/
│   ├── test_ingestion.py               # Data pipeline & budget tier tests
│   ├── test_models.py                  # Pydantic schema validation tests
│   ├── test_filter.py                  # Stage 1 filtering & SLA benchmark tests
│   ├── test_llm_service.py             # Stage 2 Groq prompt & fallback tests
│   ├── test_api.py                     # FastAPI endpoint integration tests
│   ├── test_ui.py                      # Streamlit helper & hybrid caller tests
│   ├── test_persona_eval.py            # Pytest persona evaluation tests
│   └── run_persona_eval.py             # Standalone Golden Persona benchmark
│
├── requirements.txt                    # Pinned Python dependencies
├── zomoto-plan.md                      # Project master blueprint
├── zomoto-architecture.md              # Architectural diagrams & data flows
├── zomoto-implementation-plan.md       # Phased implementation roadmap
├── zomoto-edge-case.md                 # Corner case specifications & mitigations
└── zomoto-eval.md                      # Evaluation framework & quality gates
```

---

## 🛠️ Quickstart & Execution Runbook

### 1. Environment & Setup
The project requires Python 3.11+.

```powershell
# Create virtual environment
python -m venv .venv

# Activate and install dependencies
.\.venv\Scripts\pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and set your Groq API key:

```ini
GROQ_API_KEY=your_groq_api_key_here
ENVIRONMENT=development
DATA_PATH=data/processed/zomato_clean.parquet
DEFAULT_LLM_MODEL=openai/gpt-oss-120b
```

*(Note: If `GROQ_API_KEY` is not provided, the system seamlessly runs in local heuristic fallback mode).*

### 3. Run Data Ingestion (Already Preprocessed)
To re-ingest and clean the Hugging Face dataset:

```powershell
.\.venv\Scripts\python scripts/ingest_data.py
```

### 4. Run Test Suite
Run the full automated test suite (94 tests):

```powershell
.\.venv\Scripts\pytest tests/ -v
```

### 5. Run Golden Persona Benchmark
Run the standalone persona evaluation benchmark:

```powershell
.\.venv\Scripts\python tests/run_persona_eval.py
```

### 6. Launch Backend & Frontend Concurrently (One-Command)
To start both the FastAPI backend and the Streamlit frontend together in separate terminal windows:

**Option A — Via Batch file (CMD or PowerShell):**
```cmd
.\run_app.bat
```

**Option B — Via PowerShell script:**
```powershell
.\run_app.ps1
```

---

### 7. Launch Manually in Separate Terminals

#### Terminal 1: Launch FastAPI REST Server
```powershell
.\.venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
- Interactive Swagger documentation: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Health check: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

#### Terminal 2: Launch Streamlit Web UI
```powershell
.\.venv\Scripts\streamlit run app/ui/streamlit_app.py --server.port 8501
```
- Open browser at: [http://localhost:8501](http://localhost:8501)

---

## 📊 Evaluation Scorecard

```
======================================================================
AI RESTAURANT RECOMMENDER - PERSONA EVALUATION BENCHMARK
======================================================================
PER-01 [Budget Student Hangout   ]: PASSED (Groundedness: 100%, Relevance: 4.7/5)
PER-02 [Luxury Romantic Date     ]: PASSED (Groundedness: 100%, Relevance: 4.7/5)
PER-03 [Family Sunday Brunch     ]: PASSED (Groundedness: 100%, Relevance: 4.7/5)
PER-04 [Vegan / Healthy Lunch    ]: PASSED (Groundedness: 100%, Relevance: 4.7/5)
PER-05 [Late Night Quick Bite    ]: PASSED (Groundedness: 100%, Relevance: 4.7/5)
----------------------------------------------------------------------
Circuit Breaker Fallback Mode Test: PASSED (Graceful degradation confirmed)
----------------------------------------------------------------------
Overall Groundedness: 100.0% (0 Hallucinations)
Average Response Time: 0.01s (SLA Target: <2.0s)
STATUS: ALL QUALITY GATES CLEARED (100% Persona Success)
======================================================================
```
