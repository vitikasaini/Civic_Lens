"""
CivicLens V1.0 — Backend Entry Point

FastAPI application for civic issue management and decision-support.
Provides APIs for complaint submission, processing, and authority dashboard.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="CivicLens API",
    description="AI-assisted civic issue management and decision-support platform",
    version="1.0.0",
)

# Allow frontend dev server to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Health"])
def root():
    """Health check endpoint."""
    return {"status": "ok", "project": "CivicLens", "version": "1.0.0"}


@app.get("/health", tags=["Health"])
def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "components": {
            "api": "up",
            "database": "not_initialized",  # Will be updated in Phase 1
            "ml_models": "not_loaded",       # Will be updated in Phase 2/3
        },
    }
