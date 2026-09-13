"""
SatQuery AI — Trace Route

GET /api/trace/{query_id} — Re-fetch a past execution trace.
GET /api/traces — List all stored traces.
"""

from fastapi import APIRouter, HTTPException
from backend.services.trace_builder import get_trace, get_all_traces

router = APIRouter(prefix="/api", tags=["trace"])


@router.get("/trace/{query_id}")
async def get_execution_trace(query_id: str):
    """Retrieve an execution trace by query ID."""
    trace = get_trace(query_id)
    if not trace:
        raise HTTPException(status_code=404, detail=f"Trace not found for query_id: {query_id}")
    return trace


@router.get("/traces")
async def list_traces():
    """List all stored execution traces (most recent first)."""
    traces = get_all_traces()
    return {
        "traces": traces,
        "total": len(traces),
    }
