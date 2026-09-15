"""
SatQuery AI — NASA APOD Integration Service

Handles fetching Astronomy Picture of the Day (APOD) metadata and imagery
from science.nasa.gov APOD REST API.
"""

from __future__ import annotations

import re
import uuid
import logging
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Optional, Any

import httpx

from backend.config import NASA_BASE_URL, NASA_API_KEY, UPLOAD_DIR

logger = logging.getLogger("satquery.nasa")

# Shared httpx client with connection pooling and sensible defaults
_client = httpx.Client(
    timeout=httpx.Timeout(15.0, connect=5.0),
    follow_redirects=True,
    headers={
        "User-Agent": "SatQueryAI/1.0",
        "Accept": "application/json",
    },
)


def _strip_html(text: str) -> str:
    """Remove HTML tags and normalize whitespace."""
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def _make_request(url: str) -> tuple[int, dict[str, str], Any]:
    """Execute HTTP GET with NASA API headers."""
    headers = {}
    if NASA_API_KEY:
        headers["X-API-KEY"] = NASA_API_KEY

    response = _client.get(url, headers=headers)
    response.raise_for_status()
    return response.status_code, dict(response.headers), response.json()


def normalize_apod_item(item: dict) -> dict:
    """Standardize NASA APOD item fields."""
    explanation_html = item.get("explanation", "")
    explanation_clean = _strip_html(explanation_html)

    # Prefer hdurl, fallback to url
    image_url = item.get("hdurl") or item.get("url") or ""

    return {
        "date": item.get("date", ""),
        "post_id": item.get("post_id"),
        "title": item.get("title", "Untitled NASA APOD"),
        "media_type": item.get("media_type", "image"),
        "image_url": image_url,
        "hdurl": item.get("hdurl", ""),
        "url": item.get("url", ""),
        "explanation": explanation_clean,
        "explanation_html": explanation_html,
        "credit": _strip_html(item.get("credit", "")),
        "copyright": _strip_html(item.get("copyright", "")),
        "permalink": item.get("permalink", ""),
        "alt": item.get("alt", ""),
    }


def fetch_apod_list(
    count: int = 10,
    page: int = 1,
    search: Optional[str] = None,
) -> dict:
    """
    Fetch a paginated list of APOD entries from science.nasa.gov.
    """
    params: dict[str, Any] = {
        "per_page": max(1, min(count, 100)),
        "page": max(1, page),
    }
    if search and search.strip():
        params["search"] = search.strip()
    if NASA_API_KEY:
        params["api_key"] = NASA_API_KEY

    query_str = urllib.parse.urlencode(params)
    full_url = f"{NASA_BASE_URL}?{query_str}"

    try:
        status, headers, raw_data = _make_request(full_url)
        items = []
        if isinstance(raw_data, list):
            items = [normalize_apod_item(item) for item in raw_data]
        elif isinstance(raw_data, dict):
            items = [normalize_apod_item(raw_data)]

        return {
            "success": True,
            "total_items": int(headers.get("x-wp-total", len(items))),
            "total_pages": int(headers.get("x-wp-totalpages", 1)),
            "page": page,
            "count": len(items),
            "items": items,
        }
    except Exception as e:
        logger.error(f"Failed to fetch APOD list: {e}")
        return {
            "success": False,
            "error": str(e),
            "items": [],
            "count": 0,
        }


def fetch_apod_by_date(date_str: str) -> dict:
    """
    Fetch single APOD entry by date.
    Accepts: 'YYYY-MM-DD' or 'YYMMDD'.
    """
    # Clean string
    cleaned = date_str.strip().replace("/", "-")
    code = cleaned

    # Try parsing YYYY-MM-DD to YYMMDD
    if "-" in cleaned:
        try:
            dt = datetime.strptime(cleaned, "%Y-%m-%d")
            code = dt.strftime("%y%m%d")
        except ValueError:
            pass

    full_url = f"{NASA_BASE_URL}/{code}"
    if NASA_API_KEY:
        full_url += f"?api_key={urllib.parse.quote(NASA_API_KEY)}"

    try:
        status, headers, raw_data = _make_request(full_url)
        if isinstance(raw_data, list) and len(raw_data) > 0:
            raw_data = raw_data[0]

        item = normalize_apod_item(raw_data)
        return {
            "success": True,
            "item": item,
        }
    except Exception as e:
        logger.error(f"Failed to fetch APOD by date {date_str}: {e}")
        return {
            "success": False,
            "error": str(e),
            "item": None,
        }


def import_apod_to_session(image_url: str, title: str = "NASA APOD", date_str: str = "") -> dict:
    """
    Download an APOD image and initialize it as an uploaded image session in SatQuery AI.
    """
    if not image_url:
        raise ValueError("Image URL is required for import.")

    session_id = str(uuid.uuid4())[:8]
    session_dir = UPLOAD_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    # Determine extension
    ext = ".jpg"
    parsed_path = urllib.parse.urlparse(image_url).path.lower()
    if parsed_path.endswith(".png"):
        ext = ".png"
    elif parsed_path.endswith(".tif") or parsed_path.endswith(".tiff"):
        ext = ".tif"

    filename = f"image_1_nasa_apod_{date_str or 'recent'}{ext}"
    dest_path = session_dir / filename

    # Download image with httpx
    response = _client.get(image_url)
    response.raise_for_status()
    dest_path.write_bytes(response.content)

    # Validate image via SatQuery input checker if available
    try:
        from backend.services.input_checker import validate_single_image
        validation = validate_single_image(dest_path)
    except Exception as val_err:
        validation = {
            "format": ext,
            "filename": filename,
            "status": "ready",
            "warning": f"Detailed image inspection deferred: {val_err}"
        }

    return {
        "success": True,
        "session_id": session_id,
        "filename": filename,
        "file_path": str(dest_path),
        "title": title,
        "validation": validation,
    }
