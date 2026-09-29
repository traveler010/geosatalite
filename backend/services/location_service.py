"""
SatQuery AI — Location & Geocoding Service

Provides place name geocoding, reverse geocoding, and AOI bounding box construction
using OpenStreetMap Nominatim with polite headers and in-memory caching.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional
import httpx

from backend.core.logging import get_logger

logger = get_logger("services.location")

NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"

# In-memory geocode cache
_GEOCODE_CACHE: Dict[str, Dict[str, Any]] = {}


class LocationService:
    """Geocoding, reverse geocoding, and spatial AOI calculation service."""

    @staticmethod
    async def geocode_place_name(place_name: str) -> Optional[Dict[str, Any]]:
        """Geocode a place name into latitude, longitude, and bounding box."""
        key = place_name.strip().lower()
        if key in _GEOCODE_CACHE:
            return _GEOCODE_CACHE[key]

        headers = {"User-Agent": "SatQueryAI-GeospatialAssistant/1.0"}
        params = {"q": place_name, "format": "json", "limit": 1}

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                r = await client.get(NOMINATIM_SEARCH_URL, params=params, headers=headers)
                if r.status_code == 200 and r.json():
                    item = r.json()[0]
                    lat = float(item["lat"])
                    lon = float(item["lon"])
                    # Nominatim returns bbox as [minlat, maxlat, minlon, maxlon]
                    raw_box = item.get("boundingbox", [lat - 0.05, lat + 0.05, lon - 0.05, lon + 0.05])
                    bbox = [float(raw_box[2]), float(raw_box[0]), float(raw_box[3]), float(raw_box[1])]  # [min_lon, min_lat, max_lon, max_lat]

                    result = {
                        "name": item.get("display_name", place_name),
                        "latitude": lat,
                        "longitude": lon,
                        "bbox": bbox,
                    }
                    _GEOCODE_CACHE[key] = result
                    return result
        except Exception as err:
            logger.warning(f"Geocoding failed for '{place_name}': {err}")

        # Fallback for prominent Indian / Global landmarks if network unavailable
        presets = {
            "new delhi": {"latitude": 28.6139, "longitude": 77.2090, "name": "New Delhi, India"},
            "delhi": {"latitude": 28.6139, "longitude": 77.2090, "name": "New Delhi, India"},
            "mumbai": {"latitude": 19.0760, "longitude": 72.8777, "name": "Mumbai, Maharashtra, India"},
            "bengaluru": {"latitude": 12.9716, "longitude": 77.5946, "name": "Bengaluru, Karnataka, India"},
            "bangalore": {"latitude": 12.9716, "longitude": 77.5946, "name": "Bengaluru, Karnataka, India"},
            "varanasi": {"latitude": 25.3176, "longitude": 82.9739, "name": "Varanasi, Uttar Pradesh, India"},
            "thar desert": {"latitude": 26.9157, "longitude": 70.9083, "name": "Thar Desert, Rajasthan, India"},
            "suez canal": {"latitude": 30.7050, "longitude": 32.3440, "name": "Suez Canal, Egypt"},
        }
        for preset_name, data in presets.items():
            if preset_name in key:
                lat = data["latitude"]
                lon = data["longitude"]
                result = {
                    "name": data["name"],
                    "latitude": lat,
                    "longitude": lon,
                    "bbox": [lon - 0.05, lat - 0.05, lon + 0.05, lat + 0.05],
                }
                _GEOCODE_CACHE[key] = result
                return result

        return None

    @staticmethod
    async def reverse_geocode(lat: float, lon: float) -> str:
        """Resolve latitude/longitude into human-readable place description."""
        cache_key = f"{round(lat, 4)},{round(lon, 4)}"
        if cache_key in _GEOCODE_CACHE:
            return _GEOCODE_CACHE[cache_key]["name"]

        headers = {"User-Agent": "SatQueryAI-GeospatialAssistant/1.0"}
        params = {"lat": lat, "lon": lon, "format": "json"}

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                r = await client.get(NOMINATIM_REVERSE_URL, params=params, headers=headers)
                if r.status_code == 200 and r.json():
                    name = r.json().get("display_name", f"{lat:.3f}°, {lon:.3f}°")
                    _GEOCODE_CACHE[cache_key] = {"name": name}
                    return name
        except Exception:
            pass

        return f"{lat:.4f}°, {lon:.4f}°"

    @staticmethod
    def calculate_aoi_bbox(lat: float, lon: float, radius_km: float = 5.0) -> List[float]:
        """
        Calculate an Area of Interest (AOI) bounding box [min_lon, min_lat, max_lon, max_lat]
        around a center coordinate with radius in km.
        """
        # 1 deg latitude ~= 111.32 km
        lat_delta = radius_km / 111.32
        # 1 deg longitude ~= 111.32 km * cos(lat)
        lon_delta = radius_km / (111.32 * math.cos(math.radians(lat)) or 1.0)

        min_lon = round(lon - lon_delta, 6)
        min_lat = round(lat - lat_delta, 6)
        max_lon = round(lon + lon_delta, 6)
        max_lat = round(lat + lat_delta, 6)

        return [min_lon, min_lat, max_lon, max_lat]
