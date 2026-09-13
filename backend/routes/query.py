"""
SatQuery AI — Query Route

POST /api/query — The main pipeline endpoint.
Body: {query, image_refs[]} → runs the full controller pipeline,
returns answer + evidence + trace.
"""

from __future__ import annotations

import os
import uuid
import json
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional

from backend.config import UPLOAD_DIR
from backend.services.controller import execute_query

router = APIRouter(prefix="/api", tags=["query"])


@router.post("/query")
async def run_query(
    query: Optional[str] = Form(None),
    prompt: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    modality_hints: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    image2: Optional[UploadFile] = File(None),
    image_paths: Optional[str] = Form(None),
    image_url: Optional[str] = Form(None),
):
    """
    Run a natural-language query against uploaded imagery.

    Accepts:
      - query / prompt: text question
      - image / image2: uploaded image file(s)
      - image_paths: JSON array of previously uploaded file paths (from /api/upload)
      - image_url: optional image reference (e.g. from globe layer)
      - location: JSON string of {latitude, longitude, altitude}
      - modality_hints: comma-separated modality hints
    """
    query_text = (query or prompt or "").strip()
    if not query_text:
        raise HTTPException(status_code=400, detail="Query or prompt text is required.")

    # Parse location
    loc = None
    if location:
        try:
            loc = json.loads(location)
        except json.JSONDecodeError:
            pass

    # Parse modality hints
    hints = []
    if modality_hints:
        hints = [h.strip() for h in modality_hints.split(",")]

    # Collect file paths
    file_paths = []

    # Option 1: Previously uploaded paths
    if image_paths:
        try:
            paths = json.loads(image_paths)
            if isinstance(paths, list):
                file_paths.extend(paths)
        except json.JSONDecodeError:
            pass

    # Option 2: Inline uploaded files
    for upload_file in [image, image2]:
        if upload_file and upload_file.filename:
            session_id = str(uuid.uuid4())[:8]
            session_dir = UPLOAD_DIR / session_id
            session_dir.mkdir(parents=True, exist_ok=True)
            file_path = session_dir / upload_file.filename
            with open(file_path, "wb") as f:
                content = await upload_file.read()
                f.write(content)
            file_paths.append(str(file_path))

    # Pad hints
    while len(hints) < len(file_paths):
        hints.append("")

    # Execute the agentic pipeline
    result = execute_query(
        query=query_text,
        file_paths=file_paths,
        modality_hints=hints if hints else None,
        location=loc,
    )

    # Add backward compatibility keys for legacy frontend components
    if isinstance(result, dict) and "answer" in result:
        result["response"] = result["answer"]
        result["message"] = result["answer"]

    return result
