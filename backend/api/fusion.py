"""
SatQuery AI — Optical + SAR Fusion API Endpoints

Provides joint multimodal analysis between co-registered optical and SAR image pairs:
- Modality detection & automated optical/SAR pairing
- Water detection, Built-up extraction, and Vegetation biomass analysis
- Cross-modal explanation & concordance evidence
- High-resolution colored classification overlays
"""

from __future__ import annotations

import os
import uuid
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

import numpy as np
import torch
import rasterio

from backend.database.session import get_db
from backend.models.fusion_model import OpticalSARFusionModel
from backend.services.session_service import SessionService
from backend.storage.session_storage import get_session_storage

router = APIRouter(prefix="/api/fusion", tags=["Optical-SAR Fusion"])
fusion_model = OpticalSARFusionModel()


class FusionAnalysisRequest(BaseModel):
    session_id: str = Field(..., description="ID of active analysis session")
    optical_image_id: Optional[str] = Field(None, description="Image ID of optical scene (auto-detected if omitted)")
    sar_image_id: Optional[str] = Field(None, description="Image ID of SAR scene (auto-detected if omitted)")
    image1_id: Optional[str] = Field(None, description="Alternative Image 1 ID")
    image2_id: Optional[str] = Field(None, description="Alternative Image 2 ID")
    query: Optional[str] = Field(
        "Extract built-up structures, water bodies, and vegetation using optical and SAR fusion.",
        description="User query or analysis directive",
    )
    fusion_mode: Optional[str] = Field("deep", description="Fusion mode: 'early' or 'deep'")


@router.get("/status")
async def get_fusion_status():
    """
    Returns operating status and library versions for Rasterio, GDAL, PyTorch, and NumPy.
    """
    gdal_ver = getattr(rasterio, "__gdal_version__", "embedded")
    return {
        "status": "operational",
        "libraries": {
            "rasterio": rasterio.__version__,
            "gdal": gdal_ver,
            "torch": torch.__version__,
            "numpy": np.__version__,
            "cuda_available": torch.cuda.is_available(),
        },
        "model": fusion_model.model_name,
        "supported_targets": ["water", "built_up", "dense_vegetation", "sparse_vegetation", "bare_soil"],
    }


@router.post("/analyze")
async def analyze_optical_sar_fusion(
    payload: FusionAnalysisRequest,
    db: Session = Depends(get_db),
):
    """
    Perform deep optical and SAR multimodal fusion, produce land cover classification,
    and generate explainable evidence.
    """
    session = SessionService.get_session(db, payload.session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{payload.session_id}' not found",
        )

    # Determine image IDs
    img_id_1 = payload.optical_image_id or payload.image1_id
    img_id_2 = payload.sar_image_id or payload.image2_id

    if not img_id_1 or not img_id_2:
        # If not explicitly specified, inspect session images
        session_images = SessionService.get_session_images(db, payload.session_id)
        if len(session_images) >= 2:
            img_id_1 = session_images[0].id
            img_id_2 = session_images[1].id
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Optical + SAR fusion requires at least two images in the session.",
            )

    img1 = SessionService.get_image(db, img_id_1)
    img2 = SessionService.get_image(db, img_id_2)

    if not img1 or not os.path.exists(img1.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image '{img_id_1}' not found on disk",
        )
    if not img2 or not os.path.exists(img2.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image '{img_id_2}' not found on disk",
        )

    storage = get_session_storage(payload.session_id)
    overlay_filename = f"fusion_overlay_{uuid.uuid4().hex[:8]}.png"
    overlay_output_path = os.path.join(storage.masks_dir, overlay_filename)

    try:
        result = fusion_model.predict(
            optical_path=img1.file_path,
            sar_path=img2.file_path,
            query=payload.query or "",
            overlay_output_path=overlay_output_path,
            fusion_mode=payload.fusion_mode or "deep",
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Optical-SAR fusion pipeline failed: {err}",
        )

    overlay_url = f"/api/sessions/{payload.session_id}/masks/{overlay_filename}"
    query_id = f"fusion_{uuid.uuid4().hex[:8]}"

    # Record in database
    SessionService.record_analysis_result(
        db=db,
        session_id=payload.session_id,
        query_id=query_id,
        task_type="optical_sar_fusion",
        tool_used=result["model"],
        confidence=result["confidence"],
        answer=result["answer"],
        reasoning=result["evidence"].get("cross_modal_explanation", {}).get("concordance_evidence", [""])[0],
        evidence_json={
            "class_distribution": result["class_distribution"],
            "water_detection": result["evidence"]["water_detection"],
            "built_up_detection": result["evidence"]["built_up_detection"],
            "vegetation_analysis": result["evidence"]["vegetation_analysis"],
            "cross_modal_explanation": result["evidence"]["cross_modal_explanation"],
            "overlay_url": overlay_url,
            "optical_image": img1.filename,
            "sar_image": img2.filename,
        },
    )

    return {
        "status": "success",
        "query_id": query_id,
        "answer": result["answer"],
        "class_distribution": result["class_distribution"],
        "water_analysis": result["evidence"]["water_detection"],
        "built_up_analysis": result["evidence"]["built_up_detection"],
        "vegetation_analysis": result["evidence"]["vegetation_analysis"],
        "cross_modal_explanation": result["evidence"]["cross_modal_explanation"],
        "confidence": result["confidence"],
        "evidence": result["evidence"],
        "overlay_url": overlay_url,
        "model": result["model"],
        "latency_ms": result["latency_ms"],
    }
