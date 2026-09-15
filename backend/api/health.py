"""
SatQuery AI — Health & Diagnostics Endpoints

Evaluates backend API, SQLite database connectivity, and provider health.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.providers.registry import ProviderRegistry

router = APIRouter(tags=["Health & Diagnostics"])


@router.get("/health")
@router.get("/api/health")
async def health_check(db: Session = Depends(get_db)):
    """Comprehensive system health evaluation."""
    # Check Database
    db_status = "healthy"
    try:
        db.execute(text("SELECT 1"))
    except Exception as err:
        db_status = f"unhealthy: {err}"

    # Check Providers
    registry = ProviderRegistry.get_instance()
    provider_statuses = await registry.health_check_all()

    all_providers_ok = any(s.value in ("healthy", "mock") for s in provider_statuses.values())

    return {
        "status": "healthy" if db_status == "healthy" and all_providers_ok else "degraded",
        "service": "SatQuery AI",
        "database": db_status,
        "providers": {name: status.value for name, status in provider_statuses.items()},
    }
