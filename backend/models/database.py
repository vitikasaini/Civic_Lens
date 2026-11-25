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


def run_migrations(eng):
    """Run safe, additive ALTER TABLE migrations for new columns."""
    from sqlalchemy import text, inspect
    inspector = inspect(eng)

    # Add citizen_id to complaints if missing
    if "complaints" in inspector.get_table_names():
        cols = [c["name"] for c in inspector.get_columns("complaints")]
        with eng.connect() as conn:
            if "citizen_id" not in cols:
                conn.execute(text("ALTER TABLE complaints ADD COLUMN citizen_id INTEGER REFERENCES users(id)"))
            if "address" not in cols:
                conn.execute(text("ALTER TABLE complaints ADD COLUMN address VARCHAR(500)"))
            conn.commit()


def init_db(target_engine=None):
    """
    Initialize database schema idempotently.
    Creates all tables defined in Base metadata if they don't already exist.
    Also runs safe ALTER TABLE migrations for newly-added columns.
    """
    # Import models to register them with Base metadata
    from backend.models.complaint import Complaint, StatusHistory  # noqa
    from backend.models.user import User  # noqa
    from backend.models.notification import Notification  # noqa

    eng = target_engine or engine
    Base.metadata.create_all(bind=eng)
    run_migrations(eng)
