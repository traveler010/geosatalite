"""
SatQuery AI — Database Engine & Session Management

SQLAlchemy SQLite setup with WAL mode for concurrent read/write operations.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from backend.core.logging import get_logger

logger = get_logger("database.session")

DB_DIR = Path(__file__).resolve().parent.parent
DB_PATH = DB_DIR / "satquery.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)


# Enable SQLite WAL (Write-Ahead Logging) mode and foreign keys
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a thread-safe database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
