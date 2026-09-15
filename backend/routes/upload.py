"""
SatQuery AI — Upload Route

POST /api/upload — Upload image(s), returns validated metadata
(modality, format, CRS, resolution) or a compatibility error.
"""

from __future__ import annotations

import os
import re
import uuid
import shutil
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional

from backend.config import UPLOAD_DIR, MAX_UPLOAD_SIZE_BYTES, ALLOWED_MIME_TYPES
from backend.services.input_checker import check_compatibility, validate_single_image

router = APIRouter(prefix="/api", tags=["upload"])

# ── File signature (magic bytes) validation ──────────────

_MAGIC_BYTES = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"II\x2a\x00": "image/tiff",      # TIFF little-endian
    b"MM\x00\x2a": "image/tiff",      # TIFF big-endian
    b"II\x2b\x00": "image/tiff",      # BigTIFF little-endian
    b"MM\x00\x2b": "image/tiff",      # BigTIFF big-endian
}


def _detect_mime(content: bytes) -> str | None:
    """Detect MIME type from file magic bytes."""
    for signature, mime in _MAGIC_BYTES.items():
        if content[:len(signature)] == signature:
            return mime
    return None


def _sanitize_filename(name: str) -> str:
    """
    Strip path separators, null bytes, and non-safe characters.
    Keeps alphanumeric, dots, hyphens, underscores.
    """
    # Remove any path components
    name = os.path.basename(name)
    # Strip null bytes and control characters
    name = re.sub(r"[\x00-\x1f]", "", name)
    # Allow only safe characters
    name = re.sub(r"[^a-zA-Z0-9._\-]", "_", name)
    # Prevent empty or dotfile names
    if not name or name.startswith("."):
        name = f"upload_{uuid.uuid4().hex[:6]}"
    return name


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
        # Read content
        content = await upload_file.read()

        # ── Size validation ──────────────────────────────
        if len(content) > MAX_UPLOAD_SIZE_BYTES:
            # Clean up session dir on failure
            shutil.rmtree(session_dir, ignore_errors=True)
            raise HTTPException(
                status_code=413,
                detail=f"File '{upload_file.filename}' exceeds maximum size "
                       f"of {MAX_UPLOAD_SIZE_BYTES // (1024*1024)} MB.",
            )

        # ── MIME validation (magic bytes) ────────────────
        detected_mime = _detect_mime(content)
        if detected_mime is None:
            shutil.rmtree(session_dir, ignore_errors=True)
            raise HTTPException(
                status_code=415,
                detail=f"File '{upload_file.filename}' has an unrecognized format. "
                       f"Supported: JPEG, PNG, TIFF/GeoTIFF.",
            )

        # Sanitize filename
        safe_name = f"image_{i+1}_{_sanitize_filename(upload_file.filename)}"
        file_path = session_dir / safe_name

        # Save to disk
        with open(file_path, "wb") as f:
            f.write(content)

        saved_paths.append(str(file_path))
        file_infos.append({
            "original_name": upload_file.filename,
            "saved_as": safe_name,
            "size_bytes": len(content),
            "content_type": detected_mime,
        })

    # Run compatibility check
    compatibility = check_compatibility(saved_paths, hints)

    return {
        "session_id": session_id,
        "files": file_infos,
        "file_paths": saved_paths,
        "compatibility": compatibility,
    }
