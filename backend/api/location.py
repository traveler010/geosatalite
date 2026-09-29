"""
SatQuery AI — Location & Geocoding Endpoints

Geocoding place names to coordinates and reverse geocoding coordinates to addresses.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from backend.services.location_service import LocationService

router = APIRouter(prefix="/api/location", tags=["Location & Geocoding"])


@router.get("/search")
async def search_location(query: str = Query(..., min_length=2, description="Place name to search")):
    """Geocode a place name into WGS84 coordinates and bounding box."""
    result = await LocationService.geocode_place_name(query)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Could not resolve location for query '{query}'",
        )
    return result


@router.get("/reverse")
async def reverse_geocode(
    lat: float = Query(..., ge=-90.0, le=90.0, description="Latitude"),
    lon: float = Query(..., ge=-180.0, le=180.0, description="Longitude"),
):
    """Reverse geocode coordinates into a human-readable location name."""
    name = await LocationService.reverse_geocode(lat, lon)
    return {
        "latitude": lat,
        "longitude": lon,
        "display_name": name,
    }
