"""
SatQuery AI — Unified API Router

Aggregates all modular sub-routers for health, providers, sessions,
satellite data layers, geospatial location, and bi-temporal change detection.
"""

from __future__ import annotations

from fastapi import APIRouter

from backend.api.change import router as change_router
from backend.api.health import router as health_router
from backend.api.location import router as location_router
from backend.api.providers import router as providers_router
from backend.api.satellite import router as satellite_router
from backend.api.sessions import router as sessions_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(providers_router)
api_router.include_router(sessions_router)
api_router.include_router(satellite_router)
api_router.include_router(location_router)
api_router.include_router(change_router)
