"""
SatQuery AI — NASA APOD Route

Endpoints for fetching Astronomy Picture of the Day images and importing them
directly into SatQuery AI sessions.
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Query, HTTPException

from backend.services.nasa_service import (
    fetch_apod_list,
    fetch_apod_by_date,
    import_apod_to_session,
)

router = APIRouter(prefix="/api/nasa", tags=["nasa"])


class ImportApodRequest(BaseModel):
    image_url: str
    title: Optional[str] = "NASA APOD"
    date: Optional[str] = ""


@router.get("/apod")
async def get_apod_feed(
    count: int = Query(10, ge=1, le=100, description="Number of items to fetch"),
    page: int = Query(1, ge=1, description="Page number"),
    search: Optional[str] = Query(None, description="Search query string"),
):
    """
    Fetch APOD feed from science.nasa.gov.
    """
    result = fetch_apod_list(count=count, page=page, search=search)
    if not result.get("success"):
        raise HTTPException(
            status_code=502,
            detail=result.get("error", "Failed to fetch from NASA APOD"),
        )
    return result


@router.get("/apod/{date}")
async def get_apod_for_date(date: str):
    """
    Fetch APOD for a specific date (YYYY-MM-DD or YYMMDD).
    """
    result = fetch_apod_by_date(date)
    if not result.get("success"):
        raise HTTPException(
            status_code=404,
            detail=result.get("error", f"NASA APOD entry not found for {date}"),
        )
    return result


@router.post("/apod/import")
async def import_apod(payload: ImportApodRequest):
    """
    Download a NASA APOD image and create an analysis session in SatQuery AI.
    """
    try:
        session_info = import_apod_to_session(
            image_url=payload.image_url,
            title=payload.title or "NASA APOD",
            date_str=payload.date or "",
        )
        return session_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
