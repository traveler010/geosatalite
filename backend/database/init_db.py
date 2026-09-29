"""
SatQuery AI — Database Initialization

Creates all SQLAlchemy SQLite tables idempotently at application startup.
"""

from __future__ import annotations

from backend.core.logging import get_logger
from backend.database.session import Base, engine
import backend.database.models  # Ensure all models are registered with Base

logger = get_logger("database.init")


def init_db() -> None:
    """Initialize database tables."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables verified/created successfully.")
    except Exception as err:
        logger.error(f"Failed to initialize database tables: {err}", exc_info=True)
        raise err


if __name__ == "__main__":
    init_db()
