"""
CivicLens V1.0 — Backend Entry Point

FastAPI application for civic issue management and decision-support.
Provides APIs for complaint submission, processing, and authority dashboard.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.models.database import init_db, BASE_DIR
from backend.api.complaints import router as complaints_router, UPLOAD_DIR
from backend.api.dashboard import router as dashboard_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize database schema on startup."""
    init_db()
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="CivicLens API",
    description="AI-assisted civic issue management and decision-support platform",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file serving for uploaded complaint images
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# Include API routers
app.include_router(complaints_router)
app.include_router(dashboard_router)


@app.get("/", tags=["Health"])
def root():
    """Health check endpoint."""
    return {"status": "ok", "project": "CivicLens", "version": "1.0.0"}


@app.get("/health", tags=["Health"])
def health_check():
    """Detailed health check."""
    db_file = BASE_DIR / "civiclens.db"
    db_status = "connected" if db_file.exists() else "ready_to_connect"

    return {
        "status": "healthy",
        "components": {
            "api": "up",
            "database": db_status,
            "ml_models": "not_loaded",  # Will be updated in Phase 2/3
        },
    }
