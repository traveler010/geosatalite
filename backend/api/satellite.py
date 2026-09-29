"""
SatQuery AI — Satellite Data API Endpoints

Exposes search, AOI preview fetching, and historical time series for
Copernicus Sentinel-2 (optical) and Sentinel-1 (SAR) imagery.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.providers.base import SatelliteProduct
from backend.services.satellite_service import SatelliteService

router = APIRouter(prefix="/api/satellite", tags=["Satellite Data Layer"])
satellite_service = SatelliteService()


class SatelliteSearchRequest(BaseModel):
    query: Optional[str] = Field(None, description="Place name or location search string (e.g., 'New Delhi', 'Cairo')")
    coordinates: Optional[List[float]] = Field(None, description="[latitude, longitude] pair")
    bbox: Optional[List[float]] = Field(None, description="[min_lon, min_lat, max_lon, max_lat] bounding box")
    start_date: Optional[str] = Field(None, description="Start date (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="End date (YYYY-MM-DD)")
    max_cloud_cover: float = Field(20.0, ge=0.0, le=100.0, description="Max cloud cover percentage")
    sensor: Optional[str] = Field(None, description="Sensor filter: 'Sentinel-2', 'Sentinel-1', or 'NASA'")
    limit: int = Field(10, ge=1, le=50, description="Max number of scenes to return")


class FetchAOIRequest(BaseModel):
    session_id: str = Field(..., description="Target session ID")
    product: Dict[str, Any] = Field(..., description="SatelliteProduct dictionary from search")
    bbox: Optional[List[float]] = Field(None, description="Optional AOI bbox to crop")


@router.post("/search")
async def search_satellite_imagery(payload: SatelliteSearchRequest):
    """Search for satellite imagery matching spatial and temporal criteria."""
    try:
        results = await satellite_service.search_satellite_imagery(
            query=payload.query,
            coordinates=payload.coordinates,
            bbox=payload.bbox,
            start_date=payload.start_date,
            end_date=payload.end_date,
            max_cloud_cover=payload.max_cloud_cover,
            sensor=payload.sensor,
            limit=payload.limit,
        )
        return results
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Satellite search failed: {err}",
        )


@router.post("/fetch")
async def fetch_aoi_preview(payload: FetchAOIRequest):
    """
    Fetch an AOI preview image into the specified session directory.
    Caches the cropped preview without downloading full multi-gigabyte scenes.
    """
    try:
        prod = SatelliteProduct(**payload.product)
        saved_path = await satellite_service.fetch_aoi_preview_to_session(
            product=prod,
            session_id=payload.session_id,
            bbox=payload.bbox,
        )
        return {
            "status": "cached",
            "session_id": payload.session_id,
            "product_id": prod.product_id,
            "preview_path": saved_path,
        }
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch satellite preview: {err}",
        )


@router.get("/history")
async def get_satellite_history(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    years_back: int = Query(default=3, ge=1, le=10, description="Years of historical timeline"),
    sensor: str = Query(default="Sentinel-2", description="Sensor name"),
):
    """Retrieve historical timeline of acquisitions for bi-temporal change monitoring."""
    try:
        history = await satellite_service.get_historical_series(
            coordinates=[lat, lon],
            years_back=years_back,
            sensor=sensor,
        )
        return {
            "coordinates": [lat, lon],
            "sensor": sensor,
            "timeline": history,
        }
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch satellite history: {err}",
        )
