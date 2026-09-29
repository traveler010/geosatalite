"""
SatQuery AI — Session & Storage API Endpoints

Provides REST endpoints for session lifecycle, relational history, and
direct serving of preview images, change masks, and PDF reports from
the isolated session storage directory (backend/storage/sessions/{sessionId}/).
"""

from __future__ import annotations

import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.services.session_service import SessionService
from backend.storage.session_storage import get_session_storage

router = APIRouter(prefix="/api/sessions", tags=["Sessions & Storage"])


class CreateSessionRequest(BaseModel):
    title: Optional[str] = "New Satellite Session"
    location_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_session(
    payload: CreateSessionRequest,
    db: Session = Depends(get_db),
):
    """Create a new exploration session and initialize its isolated storage sandbox."""
    session = SessionService.create_session(
        db=db,
        title=payload.title,
        location_name=payload.location_name,
        latitude=payload.latitude,
        longitude=payload.longitude,
    )
    # Ensure physical storage directory structure exists
    get_session_storage(session.id)

    return {
        "session_id": session.id,
        "title": session.title,
        "location_name": session.location_name,
        "latitude": session.latitude,
        "longitude": session.longitude,
        "created_at": session.created_at.isoformat() if session.created_at else None,
    }


@router.get("")
async def list_sessions(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """List recent sessions."""
    sessions = SessionService.list_sessions(db=db, limit=limit, offset=offset)
    return {
        "count": len(sessions),
        "sessions": [
            {
                "id": s.id,
                "title": s.title,
                "location_name": s.location_name,
                "latitude": s.latitude,
                "longitude": s.longitude,
                "image_count": len(s.images) if s.images else 0,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in sessions
        ],
    }


@router.get("/{session_id}")
async def get_session(
    session_id: str,
    db: Session = Depends(get_db),
):
    """Get full details of a session including uploaded images, metadata, and analysis results."""
    session = SessionService.get_session(db=db, session_id=session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found",
        )

    images_data = []
    for img in session.images:
        meta = img.metadata_entry
        images_data.append({
            "id": img.id,
            "filename": img.filename,
            "file_size_bytes": img.file_size_bytes,
            "mime_type": img.mime_type,
            "format": img.format,
            "preview_url": f"/api/sessions/{session_id}/images/{img.id}/preview" if img.preview_path else None,
            "metadata": {
                "crs": meta.crs if meta else None,
                "bounds_wgs84": meta.bounds_wgs84 if meta else None,
                "resolution_x": meta.resolution_x if meta else None,
                "resolution_y": meta.resolution_y if meta else None,
                "width": meta.width if meta else None,
                "height": meta.height if meta else None,
                "band_count": meta.band_count if meta else None,
                "is_geotiff": meta.is_geotiff if meta else False,
                "is_multispectral": meta.is_multispectral if meta else False,
            } if meta else None,
        })

    results_data = [
        {
            "id": r.id,
            "query_id": r.query_id,
            "task_type": r.task_type,
            "tool_used": r.tool_used,
            "confidence": r.confidence,
            "answer": r.answer,
            "evidence": r.evidence_json,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in session.analysis_results
    ]

    return {
        "id": session.id,
        "title": session.title,
        "location_name": session.location_name,
        "latitude": session.latitude,
        "longitude": session.longitude,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "images": images_data,
        "analysis_results": results_data,
    }


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    db: Session = Depends(get_db),
):
    """Delete a session and all its associated database records."""
    success = SessionService.delete_session(db=db, session_id=session_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found",
        )
    return {"status": "deleted", "session_id": session_id}


@router.get("/{session_id}/images/{image_id}/preview")
async def get_image_preview(
    session_id: str,
    image_id: str,
    db: Session = Depends(get_db),
):
    """Serve normalized PNG preview for an uploaded image."""
    img = SessionService.get_image(db=db, image_id=image_id)
    if not img or not img.preview_path or not os.path.exists(img.preview_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Preview for image '{image_id}' not found",
        )
    return FileResponse(img.preview_path, media_type="image/png")


@router.get("/{session_id}/masks/{filename}")
async def get_session_mask(
    session_id: str,
    filename: str,
):
    """Serve generated change detection mask or overlay PNG."""
    storage = get_session_storage(session_id)
    mask_path = os.path.join(storage.masks_dir, filename)
    if not os.path.exists(mask_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mask '{filename}' not found for session '{session_id}'",
        )
    return FileResponse(mask_path, media_type="image/png")


@router.get("/{session_id}/reports/{filename}")
async def get_session_report(
    session_id: str,
    filename: str,
):
    """Serve generated audit PDF report."""
    storage = get_session_storage(session_id)
    report_path = os.path.join(storage.reports_dir, filename)
    if not os.path.exists(report_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report '{filename}' not found for session '{session_id}'",
        )
    return FileResponse(report_path, media_type="application/pdf")
