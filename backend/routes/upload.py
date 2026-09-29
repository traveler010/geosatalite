"""
SatQuery AI — Upload Route (Phase 2 Enhanced)

POST /api/upload — Upload image(s), saves to isolated session storage,
runs GeospatialProcessor validation (GeoTIFF, CRS, WGS84 bbox, resolution, bands),
generates PNG previews, records session and image in SQLite, and returns
complete compatibility metadata with 100% backward-compatibility for the frontend.
"""

from __future__ import annotations

import os
import re
import uuid
import shutil
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session

from backend.config import MAX_UPLOAD_SIZE_BYTES
from backend.core.logging import get_logger
from backend.database.session import get_db
from backend.services.geospatial_service import GeospatialProcessor
from backend.services.input_checker import check_compatibility
from backend.services.session_service import SessionService
from backend.storage.session_storage import SessionStorageManager

logger = get_logger("routes.upload")
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
    """Strip path separators, null bytes, and non-safe characters."""
    name = os.path.basename(name)
    name = re.sub(r"[\x00-\x1f]", "", name)
    name = re.sub(r"[^a-zA-Z0-9._\-]", "_", name)
    if not name or name.startswith("."):
        name = f"upload_{uuid.uuid4().hex[:6]}"
    return name


@router.post("/upload")
async def upload_images(
    files: list[UploadFile] = File(...),
    modality_hints: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """
    Upload one or two images for analysis.
    Validates GeoTIFF, CRS, resolution, bands, generates previews,
    persists records in SQLite, and returns validated metadata.
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

    # Initialize isolated session storage
    session_id = str(uuid.uuid4())[:8]
    storage = SessionStorageManager(session_id)

    # Create session record in SQLite
    session_record = SessionService.create_session(
        db=db,
        title=f"Session {session_id} - {files[0].filename}",
    )

    saved_paths = []
    file_infos = []
    preview_urls = []
    geospatial_metadata_list = []

    for i, upload_file in enumerate(files):
        content = await upload_file.read()

        # ── Size validation ──────────────────────────────
        if len(content) > MAX_UPLOAD_SIZE_BYTES:
            storage.cleanup()
            raise HTTPException(
                status_code=413,
                detail=f"File '{upload_file.filename}' exceeds maximum size "
                       f"of {MAX_UPLOAD_SIZE_BYTES // (1024*1024)} MB.",
            )

        # ── MIME validation (magic bytes) ────────────────
        detected_mime = _detect_mime(content)
        if detected_mime is None:
            storage.cleanup()
            raise HTTPException(
                status_code=415,
                detail=f"File '{upload_file.filename}' has an unrecognized format. "
                       f"Supported: JPEG, PNG, TIFF/GeoTIFF.",
            )

        # Sanitize filename and save in session storage raw/ directory
        safe_name = f"image_{i+1}_{_sanitize_filename(upload_file.filename)}"
        file_path = storage.raw_dir / safe_name

        with open(file_path, "wb") as f:
            f.write(content)

        file_path_str = str(file_path)
        saved_paths.append(file_path_str)

        # Phase 2: Full GeoTIFF & Geospatial Metadata Extraction
        geo_meta = GeospatialProcessor.validate_and_extract_metadata(file_path_str)
        geospatial_metadata_list.append(geo_meta)

        # Generate Preview PNG in storage previews/ directory
        preview_filename = f"prev_{safe_name.rsplit('.', 1)[0]}.png"
        preview_path = storage.previews_dir / preview_filename
        preview_gen_path = GeospatialProcessor.generate_preview(file_path_str, str(preview_path))

        # Register Image & Metadata in SQLite
        img_record = SessionService.add_image_to_session(
            db=db,
            session_id=session_id,
            filename=upload_file.filename,
            file_path=file_path_str,
            file_size_bytes=len(content),
            mime_type=detected_mime,
            format_type=geo_meta.get("format", "unknown"),
            metadata_dict=geo_meta,
            preview_path=preview_gen_path,
        )

        preview_url = f"/api/sessions/{session_id}/images/{img_record.id}/preview"
        preview_urls.append(preview_url)

        file_infos.append({
            "original_name": upload_file.filename,
            "saved_as": safe_name,
            "size_bytes": len(content),
            "content_type": detected_mime,
            "image_id": img_record.id,
            "preview_url": preview_url,
            "geospatial": geo_meta,
        })

    # Run compatibility check
    compatibility = check_compatibility(saved_paths, hints)

    # Enrich compatibility with geospatial metadata
    if compatibility.get("metadata"):
        compatibility["metadata"]["geospatial"] = geospatial_metadata_list[0]
        if geospatial_metadata_list[0].get("bounds_wgs84"):
            compatibility["metadata"]["bounds_wgs84"] = geospatial_metadata_list[0]["bounds_wgs84"]

    return {
        "session_id": session_id,
        "files": file_infos,
        "file_paths": saved_paths,
        "preview_urls": preview_urls,
        "compatibility": compatibility,
        "geospatial_metadata": geospatial_metadata_list,
    }
