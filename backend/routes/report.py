"""
SatQuery AI — Report Route

GET /api/report/{query_id} — Generate and download a report.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from backend.services.trace_builder import get_trace
from backend.services.report_generator import generate_html_report, get_report_path

router = APIRouter(prefix="/api", tags=["report"])


@router.get("/report/{query_id}")
async def download_report(query_id: str):
    """Generate (if needed) and return an HTML report for a query."""
    # Check if report already exists
    existing = get_report_path(query_id)
    if existing:
        return FileResponse(
            existing,
            media_type="text/html",
            filename=f"satquery_report_{query_id}.html",
        )

    # Generate from trace
    trace = get_trace(query_id)
    if not trace:
        raise HTTPException(
            status_code=404,
            detail=f"No trace found for query_id: {query_id}. Run a query first.",
        )

    report_path = generate_html_report(trace, query_id)
    return FileResponse(
        report_path,
        media_type="text/html",
        filename=f"satquery_report_{query_id}.html",
    )
