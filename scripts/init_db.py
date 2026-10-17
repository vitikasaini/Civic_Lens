"""
Standalone database initialization script for CivicLens.
Creates the SQLite database and all required tables idempotently.
"""

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.models.database import init_db, engine, DEFAULT_DB_PATH


def main():
    print(f"Initializing CivicLens database at: {DEFAULT_DB_PATH}")
    init_db()
    print("Database tables created successfully!")
    print(f"Database file exists: {DEFAULT_DB_PATH.exists()}")


if __name__ == "__main__":
    main()
