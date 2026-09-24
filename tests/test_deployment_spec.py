"""Unit and configuration tests for production deployment specifications.

Validates that Dockerfile, railway.json, vercel.json, Procfile, and .gitignore
conform to the production deployment plan.
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent


def test_dockerfile_specification():
    """Verify Dockerfile presence and essential production directives."""
    dockerfile = ROOT_DIR / "Dockerfile"
    assert dockerfile.exists(), "Dockerfile must exist in project root."
    content = dockerfile.read_text(encoding="utf-8")

    assert "FROM python:" in content
    assert "WORKDIR /app" in content
    assert "HEALTHCHECK" in content
    assert "/health" in content
    assert "EXPOSE" in content
    assert "CMD" in content
    assert "${PORT}" in content
    assert "appuser" in content, "Dockerfile should create and use a non-root user."


def test_railway_json_validity():
    """Verify railway.json syntax and required orchestration properties."""
    railway_file = ROOT_DIR / "railway.json"
    assert railway_file.exists(), "railway.json must exist in project root."
    data = json.loads(railway_file.read_text(encoding="utf-8"))

    assert data.get("build", {}).get("builder") == "DOCKERFILE"
    assert data.get("build", {}).get("dockerfilePath") == "Dockerfile"
    assert data.get("deploy", {}).get("healthcheckPath") == "/health"


def test_vercel_json_rewrites_and_headers():
    """Verify vercel.json contains edge rewrites for Zero-CORS and security headers."""
    vercel_file = ROOT_DIR / "vercel.json"
    assert vercel_file.exists(), "vercel.json must exist in project root."
    data = json.loads(vercel_file.read_text(encoding="utf-8"))

    rewrites = data.get("rewrites", [])
    assert len(rewrites) >= 3, "vercel.json must contain edge rewrites."

    sources = [r.get("source") for r in rewrites]
    assert "/api/:path*" in sources, "Must rewrite /api/:path* to backend."
    assert "/health" in sources, "Must rewrite /health to backend."
    assert "/" in sources, "Must rewrite root / to frontend index.html."

    headers = data.get("headers", [])
    assert len(headers) >= 1, "vercel.json must specify security headers."


def test_procfile_dynamic_port():
    """Verify Procfile specifies dynamic $PORT binding for PaaS runners."""
    procfile = ROOT_DIR / "Procfile"
    assert procfile.exists(), "Procfile must exist in project root."
    content = procfile.read_text(encoding="utf-8").strip()
    assert "PORT" in content
    assert "uvicorn app.main:app" in content


def test_dockerignore_rules():
    """Verify .dockerignore excludes virtualenv and sensitive files."""
    dockerignore = ROOT_DIR / ".dockerignore"
    assert dockerignore.exists(), ".dockerignore must exist."
    content = dockerignore.read_text(encoding="utf-8")
    assert ".venv/" in content
    assert ".env" in content
    assert "tests/" in content


def test_gitignore_tracks_clean_parquet():
    """Verify .gitignore tracks clean Parquet dataset for instant deployment."""
    gitignore = ROOT_DIR / ".gitignore"
    assert gitignore.exists()
    content = gitignore.read_text(encoding="utf-8")
    assert "!data/processed/zomato_clean.parquet" in content, (
        ".gitignore must explicitly track zomato_clean.parquet for container builds."
    )


def test_static_frontend_api_base_resolution():
    """Verify DineMind AI static frontend includes flexible API_BASE resolver."""
    index_file = ROOT_DIR / "app" / "static" / "index.html"
    assert index_file.exists(), "app/static/index.html must exist."
    content = index_file.read_text(encoding="utf-8")
    assert "API_BASE" in content
    assert "${API_BASE}/health" in content
    assert "${API_BASE}/api/v1/recommendations" in content
