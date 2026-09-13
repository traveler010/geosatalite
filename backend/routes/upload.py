"""
SatQuery AI — Upload Route

POST /api/upload — Upload image(s), returns validated metadata
(modality, format, CRS, resolution) or a compatibility error.
"""

from __future__ import annotations

import os
import uuid
import shutil
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional

from backend.config import UPLOAD_DIR
from backend.services.input_checker import check_compatibility, validate_single_image

router = APIRouter(prefix="/api", tags=["upload"])


@router.post("/upload")
async def upload_images(
    files: list[UploadFile] = File(...),
    modality_hints: Optional[str] = Form(None),
):
    """
    Upload one or two images for analysis.
    Returns validated metadata or a compatibility error.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    if len(files) > 2:
        raise HTTPException(
            status_code=400,
            detail=f"Too many files ({len(files)}). Maximum is 2.",
        )

    # Parse modality hints
    hints = []
    if modality_hints:
        hints = [h.strip() for h in modality_hints.split(",")]
    while len(hints) < len(files):
        hints.append("")

    # Save uploaded files
    session_id = str(uuid.uuid4())[:8]
    session_dir = UPLOAD_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    saved_paths = []
    file_infos = []

    for i, upload_file in enumerate(files):
        # Sanitize filename
        safe_name = f"image_{i+1}_{upload_file.filename}"
        file_path = session_dir / safe_name

        # Save to disk
        with open(file_path, "wb") as f:
            content = await upload_file.read()
            f.write(content)

        saved_paths.append(str(file_path))
        file_infos.append({
            "original_name": upload_file.filename,
            "saved_as": safe_name,
            "size_bytes": len(content),
            "content_type": upload_file.content_type,
        })

    # Run compatibility check
    compatibility = check_compatibility(saved_paths, hints)

    return {
        "session_id": session_id,
        "files": file_infos,
        "file_paths": saved_paths,
        "compatibility": compatibility,
    }
