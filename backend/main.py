"""
SatQuery AI — FastAPI Application

Main entry point. Mounts all API routes with CORS middleware.

Run with:
  cd backend
  uvicorn main:app --reload --host 0.0.0.0 --port 8000
or from project root:
  python -m uvicorn backend.main:app --reload --port 8000
"""

import sys
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
from backend.routes import upload, query, tools, trace, report, nasa, ai

app = FastAPI(
    title="SatQuery AI",
    description="Agentic Vision-Language Assistant for Multimodal Remote Sensing Image Analysis",
    version="1.0.0",
)

# ─── CORS ────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routes ──────────────────────────────────────────────
app.include_router(upload.router)
app.include_router(query.router)
app.include_router(tools.router)
app.include_router(trace.router)
app.include_router(report.router)
app.include_router(nasa.router)
app.include_router(ai.router)

# Also expose /query directly for backward-compatibility with older frontends
app.add_api_route("/query", query.run_query, methods=["POST"], include_in_schema=False)


@app.get("/")
async def root():
    return {
        "service": "SatQuery AI",
        "version": "1.0.0",
        "status": "online",
        "endpoints": [
            "POST /api/upload",
            "POST /api/query",
            "GET  /api/tools",
            "GET  /api/trace/{query_id}",
            "GET  /api/traces",
            "GET  /api/report/{query_id}",
        ],
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}
