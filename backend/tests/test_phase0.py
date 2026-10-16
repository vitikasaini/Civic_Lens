"""
Phase 0 Verification Tests

Validates:
- T0.1: docs/decisions.md covers all 6 open decisions with options and rationales.
- T0.2: Git repository is initialized and has commits.
- T0.3: Python virtual environment has all required libraries installed and importable.
- T0.4: FastAPI backend application starts and responds at / and /health and /openapi.json.
- T0.5: Frontend React/Vite project is initialized and has valid package.json and dependencies.
- T0.6: Project folder structure matches the agreed design layout.
"""

import os
import subprocess
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from backend.main import app

WORKSPACE_DIR = Path(__file__).resolve().parent.parent.parent


def test_t01_decisions_documented():
    """T0.1: Check that all 6 open decisions in Section 9 have documented answers in docs/decisions.md."""
    decisions_file = WORKSPACE_DIR / "docs" / "decisions.md"
    assert decisions_file.exists(), "docs/decisions.md does not exist"
    content = decisions_file.read_text(encoding="utf-8")

    expected_topics = [
        "Normalization Rules for Priority Factors",
        "Location-Importance List",
        "Image–Text Category Conflict Resolution",
        "Dataset Availability & Fallback Strategy",
        "Frontend Framework",
        "Deep Learning Framework",
    ]

    for topic in expected_topics:
        assert topic.lower() in content.lower(), f"Decision topic '{topic}' missing from docs/decisions.md"

    # Verify sensitive locations config file exists as created in Decision 2
    sensitive_loc_file = WORKSPACE_DIR / "backend" / "ml" / "config" / "sensitive_locations.json"
    assert sensitive_loc_file.exists(), "sensitive_locations.json does not exist"


def test_t02_git_initialized_and_committed():
    """T0.2: git log shows initial commit."""
    result = subprocess.run(
        ["git", "log", "-n", "1", "--oneline"],
        cwd=WORKSPACE_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"git log failed: {result.stderr}"
    assert len(result.stdout.strip()) > 0, "No git commit found in repository"


def test_t03_python_dependencies_importable():
    """T0.3: Required Python packages from requirements.txt are installed and cleanly importable."""
    import fastapi
    import uvicorn
    import sqlalchemy
    import sklearn
    import pandas
    import numpy
    import cv2
    import pytest
    import httpx
    import tensorflow

    assert fastapi.__version__
    assert sqlalchemy.__version__
    assert sklearn.__version__
    assert pandas.__version__
    assert numpy.__version__
    assert cv2.__version__
    assert tensorflow.__version__


def test_t04_backend_endpoints_and_docs():
    """T0.4: Backend FastAPI app responds at root, health, and openapi docs endpoints."""
    client = TestClient(app)

    # Root endpoint
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "ok"
    assert data.get("project") == "CivicLens"

    # Health endpoint
    response_health = client.get("/health")
    assert response_health.status_code == 200
    health_data = response_health.json()
    assert health_data.get("status") == "healthy"
    assert "components" in health_data

    # OpenAPI schema endpoint (backing Swagger /docs)
    response_openapi = client.get("/openapi.json")
    assert response_openapi.status_code == 200
    openapi_spec = response_openapi.json()
    assert openapi_spec.get("info", {}).get("title") == "CivicLens API"


def test_t05_frontend_project_ready():
    """T0.5: Frontend React project exists, package.json is valid, and index.html is present."""
    frontend_dir = WORKSPACE_DIR / "frontend"
    assert frontend_dir.exists(), "frontend directory does not exist"

    pkg_json = frontend_dir / "package.json"
    assert pkg_json.exists(), "frontend/package.json does not exist"

    index_html = frontend_dir / "index.html"
    assert index_html.exists(), "frontend/index.html does not exist"

    node_modules = frontend_dir / "node_modules"
    assert node_modules.exists(), "frontend/node_modules does not exist (dependencies not installed)"


def test_t06_folder_structure():
    """T0.6: Folder structure matches the agreed layout."""
    expected_directories = [
        "backend/api",
        "backend/models",
        "backend/ml/models",
        "backend/tests",
        "frontend",
        "data/images/potholes",
        "data/images/garbage",
        "data/images/waterlogging",
        "data/images/streetlight",
        "data/text",
        "notebooks",
        "scripts",
        "docs",
    ]

    for rel_path in expected_directories:
        p = WORKSPACE_DIR / rel_path
        assert p.exists() and p.is_dir(), f"Expected directory missing: {rel_path}"
