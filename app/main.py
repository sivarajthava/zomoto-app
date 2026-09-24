"""FastAPI application entrypoint for the AI-Powered Restaurant Recommendation Service."""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.models import (
    MetadataResponse,
    RecommendationResponse,
    UserPreferenceRequest,
)
from app.services.data_loader import DataLoader, get_data_loader
from app.services.recommendation_service import (
    RecommendationOrchestrator,
    get_recommendation_service,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("zomato_app")

STATIC_DIR = Path(__file__).resolve().parent / "static"
templates = Jinja2Templates(directory=str(STATIC_DIR)) if STATIC_DIR.exists() else None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown lifecycle handler."""
    logger.info("Initializing Zomato Recommendation API...")
    try:
        loader = get_data_loader()
        df = loader.df
        logger.info(f"Dataset successfully loaded: {len(df):,} restaurants ready in memory.")
    except Exception as exc:
        logger.error(f"Failed to load restaurant dataset on startup: {exc}")
    yield
    logger.info("Shutting down Zomato Recommendation API.")


app = FastAPI(
    title="Zomato AI Restaurant Recommendation API",
    description=(
        "Production-grade AI-powered restaurant discovery service combining deterministic "
        "tabular filtering with Groq LPU reasoning for personalized, grounded dining suggestions."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Mount static assets directory
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Process-Time"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Timing middleware adding X-Process-Time header to all responses."""
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = (time.perf_counter() - start_time) * 1000
    response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Format Pydantic validation errors cleanly."""
    errors = []
    for err in exc.errors():
        field = " -> ".join(str(loc) for loc in err.get("loc", []))
        errors.append({"field": field, "message": err.get("msg")})
    return JSONResponse(
        status_code=422,
        content={"detail": "Request validation failed.", "errors": errors},
    )


@app.get("/", summary="Root Index", tags=["Health & Info"])
async def root(
    request: Request,
    data_loader: DataLoader = Depends(get_data_loader),
):
    """Serve the Midnight Epicure web frontend for browsers (Jinja debug fallback), or JSON metadata for API clients."""
    accept_header = request.headers.get("accept", "")
    index_file = STATIC_DIR / "index.html"
    if "text/html" in accept_header and index_file.exists():
        if templates is not None:
            try:
                record_count = len(data_loader.df)
            except Exception:
                record_count = 0
            return templates.TemplateResponse(
                request=request,
                name="index.html",
                context={
                    "records_loaded": record_count,
                    "model": settings.default_llm_model,
                    "environment": settings.environment,
                },
            )
        return FileResponse(str(index_file))

    return {
        "service": "Zomato AI Restaurant Recommendation System",
        "status": "online",
        "docs_url": "/docs",
        "version": "1.0.0",
    }


@app.get("/app", summary="Midnight Epicure Web Frontend", tags=["Frontend"])
async def web_app(
    request: Request,
    data_loader: DataLoader = Depends(get_data_loader),
):
    """Directly serve the Midnight Epicure web frontend."""
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Frontend asset index.html not found.",
        )
    if templates is not None:
        try:
            record_count = len(data_loader.df)
        except Exception:
            record_count = 0
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "records_loaded": record_count,
                "model": settings.default_llm_model,
                "environment": settings.environment,
            },
        )
    return FileResponse(str(index_file))


@app.get("/health", summary="Health Check", tags=["Health & Info"])
async def health_check(data_loader: DataLoader = Depends(get_data_loader)):
    """Return health status and active record count."""
    try:
        record_count = len(data_loader.df)
        return {
            "status": "healthy",
            "records_loaded": record_count,
            "environment": settings.environment,
            "model": settings.default_llm_model,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service degraded: {exc}",
        )


@app.get(
    "/api/meta",
    response_model=MetadataResponse,
    summary="Filter Metadata (Shorthand)",
    tags=["Recommendations"],
)
@app.get(
    "/api/v1/metadata",
    response_model=MetadataResponse,
    summary="Filter Metadata",
    tags=["Recommendations"],
)
async def get_filter_metadata(data_loader: DataLoader = Depends(get_data_loader)):
    """Retrieve unique cities, localities, cuisines, and budget tiers for frontend selectors."""
    return data_loader.metadata


@app.post(
    "/api/recommend",
    response_model=RecommendationResponse,
    summary="Get Recommendations (Shorthand)",
    tags=["Recommendations"],
)
@app.post(
    "/api/v1/recommendations",
    response_model=RecommendationResponse,
    summary="Get Recommendations",
    tags=["Recommendations"],
)
async def recommend_restaurants(
    request: UserPreferenceRequest,
    orchestrator: RecommendationOrchestrator = Depends(get_recommendation_service),
):
    """Generate personalized, AI-curated restaurant recommendations based on user preferences."""
    try:
        response = await orchestrator.get_recommendations(request)
        return response
    except Exception as exc:
        logger.error(f"Error handling recommendation request: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate recommendations: {exc}",
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=settings.app_host, port=settings.app_port, reload=True)
