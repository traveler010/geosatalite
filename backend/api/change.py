"""
SatQuery AI — Bi-Temporal Change Detection API Endpoints

Provides co-registration, pixel-wise Otsu change detection, colored overlay generation,
and CDVQA (Change Detection Visual Question Answering) between two satellite images.
"""

from __future__ import annotations

import os
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.models.change_detector import BiTemporalChangeModel
from backend.services.session_service import SessionService
from backend.storage.session_storage import get_session_storage

router = APIRouter(prefix="/api/change", tags=["Change Detection"])
change_model = BiTemporalChangeModel()


class ChangeAnalysisRequest(BaseModel):
    session_id: str = Field(..., description="ID of active analysis session")
    image1_id: str = Field(..., description="Image ID of baseline / before image")
    image2_id: str = Field(..., description="Image ID of post-event / after image")
    query: Optional[str] = Field(
        "Describe the significant changes detected between these two dates.",
        description="Optional change query or question (e.g., 'Were new buildings constructed?')",
    )


@router.post("/analyze")
async def analyze_change(
    payload: ChangeAnalysisRequest,
    db: Session = Depends(get_db),
):
    """
    Perform co-registration, compute change mask, and run CDVQA between two uploaded scenes.
    """
    session = SessionService.get_session(db, payload.session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{payload.session_id}' not found",
        )

    img1 = SessionService.get_image(db, payload.image1_id)
    img2 = SessionService.get_image(db, payload.image2_id)

    if not img1 or not os.path.exists(img1.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Baseline image '{payload.image1_id}' not found on disk",
        )
    if not img2 or not os.path.exists(img2.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Comparison image '{payload.image2_id}' not found on disk",
        )

    storage = get_session_storage(payload.session_id)
    overlay_filename = f"change_overlay_{uuid.uuid4().hex[:8]}.png"
    overlay_output_path = os.path.join(storage.masks_dir, overlay_filename)

    try:
        result = change_model.predict(
            image1_path=img1.file_path,
            image2_path=img2.file_path,
            query=payload.query or "Describe changes",
            overlay_output_path=overlay_output_path,
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Change detection pipeline failed: {err}",
        )

    # Relative URL to overlay
    overlay_url = f"/api/sessions/{payload.session_id}/masks/{overlay_filename}"

    # Record in database
    query_id = f"cd_{uuid.uuid4().hex[:8]}"
    SessionService.record_analysis_result(
        db=db,
        session_id=payload.session_id,
        query_id=query_id,
        task_type="change_detection",
        tool_used=result["model"],
        confidence=result["confidence"],
        answer=result["answer"],
        reasoning=result.get("change_description"),
        evidence_json={
            "change_percentage": result["change_percentage"],
            "changed_regions": result["changed_regions"],
            "overlay_url": overlay_url,
            "baseline_image": img1.filename,
            "comparison_image": img2.filename,
        },
    )

    return {
        "status": "success",
        "query_id": query_id,
        "answer": result["answer"],
        "change_description": result["change_description"],
        "change_percentage": result["change_percentage"],
        "changed_regions": result["changed_regions"],
        "confidence": result["confidence"],
        "overlay_url": overlay_url,
        "latency_ms": result["latency_ms"],
    }
