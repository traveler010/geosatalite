"""
SatQuery AI — FastAPI Application (Phases 1-7 Unified)

Main entry point. Mounts all legacy and modular sub-routers,
initializes SQLite database schemas, provider registry, logging,
and global error handlers with zero breaking changes.
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

# ─── Path bootstrap: ensure backend package is always importable ──
_backend_dir = Path(__file__).resolve().parent
_project_root = _backend_dir.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import ALLOWED_ORIGINS
from backend.core.errors import register_error_handlers
from backend.core.logging import get_logger, setup_logging
from backend.database.init_db import init_db
from backend.providers.registry import ProviderRegistry

# Existing / legacy routes
from backend.routes import upload, query, tools, trace, report, nasa, ai

# New modular API router (health, providers, sessions, satellite, location, change)
from backend.api.router import api_router

logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle management."""
    setup_logging()
    logger.info("Initializing SatQuery AI database schemas...")
    init_db()

    logger.info("Verifying AI and Geospatial provider registry...")
    registry = ProviderRegistry.get_instance()
    # Pre-warm providers asynchronously
    try:
        await registry.health_check_all()
    except Exception as e:
        logger.warning(f"Provider registry warm-up warning: {e}")

    logger.info("SatQuery AI services fully operational.")
    yield
    logger.info("SatQuery AI shutting down.")


app = FastAPI(
    title="SatQuery AI",
    description="Agentic Vision-Language Assistant for Multimodal Remote Sensing Image Analysis",
    version="2.0.0",
    lifespan=lifespan,
)

# ─── Global Error Handlers ───────────────────────────────
register_error_handlers(app)

# ─── CORS ────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Modular New Subsystems ──────────────────────────────
app.include_router(api_router)

# ─── Existing Routes (Preserved for 100% Backward Compatibility) ──
app.include_router(upload.router)
app.include_router(query.router)
app.include_router(tools.router)
app.include_router(trace.router)
app.include_router(report.router)
app.include_router(nasa.router)
app.include_router(ai.router)

# Direct /query route for legacy frontends
app.add_api_route("/query", query.run_query, methods=["POST"], include_in_schema=False)


@app.get("/")
async def root():
    return {
        "service": "SatQuery AI",
        "version": "2.0.0",
        "status": "online",
        "endpoints": [
            "POST /api/upload",
            "POST /api/query",
            "GET  /api/tools",
            "GET  /api/trace/{query_id}",
            "GET  /api/traces",
            "GET  /api/report/{query_id}",
            "GET  /api/health",
            "GET  /api/providers",
            "POST /api/sessions",
            "POST /api/satellite/search",
            "POST /api/satellite/fetch",
            "GET  /api/location/search",
            "POST /api/change/analyze",
            "POST /api/fusion/analyze",
            "GET  /api/fusion/status",
        ],
    }



@app.get("/health")
async def health():
    return {"status": "healthy", "service": "SatQuery AI", "version": "2.0.0"}
