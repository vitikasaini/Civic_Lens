"""
Database connection and session management for CivicLens.
Uses SQLite for local, zero-config, portable storage.
"""

import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Project root directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Database URL can be overridden via environment variable (e.g., for testing)
DEFAULT_DB_PATH = BASE_DIR / "civiclens.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}")

# SQLite requires check_same_thread=False for multithreaded web applications
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency to yield a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(target_engine=None):
    """
    Initialize database schema idempotently.
    Creates all tables defined in Base metadata if they don't already exist.
    """
    from backend.models.complaint import Complaint, StatusHistory  # ensure models are registered
    eng = target_engine or engine
    Base.metadata.create_all(bind=eng)
