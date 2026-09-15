"""
SatQuery AI — Report Route

GET /api/report/{query_id}          — Generate and download a PDF report.
GET /api/report/{query_id}?format=html — Generate and download an HTML report.
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from backend.services.trace_builder import get_trace
from backend.services.report_generator import (
    generate_pdf_report,
    generate_html_report,
    get_report_path,
)

router = APIRouter(prefix="/api", tags=["report"])


@router.get("/report/{query_id}")
async def download_report(
    query_id: str,
    format: str = Query("pdf", description="Report format: 'pdf' or 'html'"),
):
    """Generate (if needed) and return a report for a query."""
    fmt = format.lower().strip()
    if fmt not in ("pdf", "html"):
        raise HTTPException(status_code=400, detail="Format must be 'pdf' or 'html'.")

    # Check if report already exists
    existing = get_report_path(query_id, fmt=fmt)
    if existing:
        media = "application/pdf" if existing.endswith(".pdf") else "text/html"
        ext = "pdf" if existing.endswith(".pdf") else "html"
        return FileResponse(
            existing,
            media_type=media,
            filename=f"satquery_report_{query_id}.{ext}",
        )

    # Generate from trace
    trace = get_trace(query_id)
    if not trace:
        raise HTTPException(
            status_code=404,
            detail=f"No trace found for query_id: {query_id}. Run a query first.",
        )

    if fmt == "pdf":
        report_path = generate_pdf_report(trace, query_id)
        return FileResponse(
            report_path,
            media_type="application/pdf",
            filename=f"satquery_report_{query_id}.pdf",
        )
    else:
        report_path = generate_html_report(trace, query_id)
        return FileResponse(
            report_path,
            media_type="text/html",
            filename=f"satquery_report_{query_id}.html",
        )
