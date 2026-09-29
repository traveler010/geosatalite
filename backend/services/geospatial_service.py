"""
SatQuery AI — Geospatial & Satellite Image Processing Service

Comprehensive GeoTIFF & remote sensing raster processor using:
- Rasterio (CRS, transforms, band reads, georeferencing)
- pyproj (coordinate transformations to WGS84 EPSG:4326)
- Shapely (geographic footprint polygons and bounding boxes)
- OpenCV & NumPy (percentile normalization, true/false color composite, preview rendering)
- Pillow (fallback image I/O)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from PIL import Image

try:
    import rasterio
    from rasterio.enums import ColorInterp
    from rasterio.warp import transform_bounds
    HAS_RASTERIO = True
except ImportError:
    HAS_RASTERIO = False

try:
    import pyproj
    HAS_PYPROJ = True
except ImportError:
    HAS_PYPROJ = False

try:
    from shapely.geometry import box, mapping
    HAS_SHAPELY = True
except ImportError:
    HAS_SHAPELY = False

import cv2

from backend.core.logging import get_logger
from backend.core.errors import GeospatialProcessingError

logger = get_logger("services.geospatial")


def normalize_band_percentile(band: np.ndarray, p_min: float = 2.0, p_max: float = 98.0) -> np.ndarray:
    """Normalize a raster band using cumulative percentile stretch to 0-255 uint8."""
    # Filter out nodata / invalid numbers
    valid_mask = np.isfinite(band) & (band > 0)
    if not np.any(valid_mask):
        return np.zeros(band.shape, dtype=np.uint8)

    low = np.percentile(band[valid_mask], p_min)
    high = np.percentile(band[valid_mask], p_max)

    if high <= low:
        # Min-max fallback
        low = np.min(band[valid_mask])
        high = np.max(band[valid_mask])

    if high > low:
        stretched = np.clip((band - low) / (high - low) * 255.0, 0, 255).astype(np.uint8)
    else:
        stretched = np.zeros(band.shape, dtype=np.uint8)

    return stretched


class GeospatialProcessor:
    """Processes satellite imagery, extracts geospatial metadata, and creates previews."""

    @classmethod
    def validate_and_extract_metadata(cls, image_path: str | Path) -> Dict[str, Any]:
        """Validate and extract metadata from GeoTIFF or standard raster."""
        return cls.inspect_and_process_image(image_path)

    @classmethod
    def generate_preview(cls, image_path: str | Path, output_path: str | Path, max_dim: int = 1024) -> str:
        """Generate web preview PNG."""
        return cls.generate_web_preview(image_path, output_path, max_dim=max_dim)

    @classmethod
    def inspect_and_process_image(
        cls,
        image_path: str | Path,
        preview_output_path: Optional[str | Path] = None,
    ) -> Dict[str, Any]:
        """
        Validate and extract all metadata from a GeoTIFF or standard image.
        Optionally renders a contrast-normalized PNG preview.
        """
        path = Path(image_path)
        if not path.exists():
            raise GeospatialProcessingError(f"Image not found at {path}")

        # Check for GeoTIFF / Rasterio capability
        is_geotiff = False
        crs_str = None
        crs_epsg = None
        bounds_native = None
        bounds_wgs84 = None
        footprint_geojson = None
        resolution_x = None
        resolution_y = None
        width = 0
        height = 0
        band_count = 1
        band_names = []
        data_type = "uint8"
        raw_tags = {}

        if HAS_RASTERIO:
            try:
                with rasterio.open(path) as src:
                    width = src.width
                    height = src.height
                    band_count = src.count
                    data_type = str(src.dtypes[0]) if src.dtypes else "uint8"
                    raw_tags = dict(src.tags())

                    # Inspect CRS
                    if src.crs:
                        is_geotiff = True
                        crs_str = src.crs.to_string()
                        crs_epsg = src.crs.to_epsg()

                        # Bounds in native CRS
                        bounds_native = [src.bounds.left, src.bounds.bottom, src.bounds.right, src.bounds.top]

                        # Resolution
                        res = src.res
                        resolution_x = float(res[0])
                        resolution_y = float(res[1])

                        # Convert bounds to WGS84
                        try:
                            wgs_bounds = transform_bounds(src.crs, "EPSG:4326", *bounds_native)
                            bounds_wgs84 = {
                                "min_lon": float(wgs_bounds[0]),
                                "min_lat": float(wgs_bounds[1]),
                                "max_lon": float(wgs_bounds[2]),
                                "max_lat": float(wgs_bounds[3]),
                            }
                            if HAS_SHAPELY:
                                poly = box(wgs_bounds[0], wgs_bounds[1], wgs_bounds[2], wgs_bounds[3])
                                footprint_geojson = mapping(poly)
                        except Exception as wgs_err:
                            logger.warning(f"Failed to transform bounds to WGS84: {wgs_err}")

                    # Determine band names
                    for b in range(1, band_count + 1):
                        band_names.append(f"Band_{b}")

            except rasterio.errors.RasterioIOError:
                # Not a GDAL/GeoTIFF raster, fallback to standard PIL inspection
                pass
            except Exception as err:
                logger.warning(f"Rasterio inspection warning for {path}: {err}")

        # Fallback to PIL for non-GeoTIFF standard images
        if not width or not height:
            try:
                with Image.open(path) as pil_img:
                    width, height = pil_img.size
                    mode = pil_img.mode
                    band_count = len(pil_img.getbands()) if hasattr(pil_img, "getbands") else 3
                    band_names = [f"Band_{b}" for b in pil_img.getbands()] if hasattr(pil_img, "getbands") else ["R", "G", "B"]
                    data_type = "uint8"
            except Exception as pil_err:
                raise GeospatialProcessingError(f"Failed to read image file: {pil_err}")

        # Modality determination
        is_multispectral = band_count >= 4
        if band_count == 1:
            modality = "sar"
        elif band_count == 3:
            modality = "optical"
        elif is_multispectral:
            modality = "multispectral"
        else:
            modality = "optical"

        # Preview Generation
        preview_path_str = None
        if preview_output_path:
            try:
                preview_path_str = cls.generate_web_preview(path, preview_output_path)
            except Exception as p_err:
                logger.warning(f"Could not generate preview for {path}: {p_err}")

        return {
            "is_geotiff": is_geotiff,
            "crs": crs_str,
            "crs_epsg": crs_epsg,
            "bounds_native": bounds_native,
            "bounds_wgs84": bounds_wgs84,
            "footprint": footprint_geojson,
            "resolution_x": resolution_x,
            "resolution_y": resolution_y,
            "width": width,
            "height": height,
            "band_count": band_count,
            "band_names": band_names,
            "data_type": data_type,
            "modality": modality,
            "is_multispectral": is_multispectral,
            "preview_path": preview_path_str,
            "raw_tags": raw_tags,
        }

    @classmethod
    def generate_web_preview(
        cls,
        image_path: str | Path,
        output_path: str | Path,
        max_dim: int = 1024,
    ) -> str:
        """
        Extracts True Color RGB or single-band grayscale, applies percentile normalization,
        and saves a web-ready PNG preview.
        """
        src_path = Path(image_path)
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if HAS_RASTERIO:
            try:
                with rasterio.open(src_path) as src:
                    count = src.count

                    if count >= 3:
                        # Extract first 3 bands (R, G, B)
                        r = normalize_band_percentile(src.read(1))
                        g = normalize_band_percentile(src.read(2))
                        b = normalize_band_percentile(src.read(3))
                        rgb = np.dstack((r, g, b))
                    else:
                        # Single band grayscale (e.g. SAR)
                        gray = normalize_band_percentile(src.read(1))
                        rgb = np.dstack((gray, gray, gray))

                    # Downsample if needed
                    h, w = rgb.shape[:2]
                    if max(h, w) > max_dim:
                        scale = max_dim / max(h, w)
                        new_w, new_h = int(w * scale), int(h * scale)
                        rgb = cv2.resize(rgb, (new_w, new_h), interpolation=cv2.INTER_AREA)

                    # Save as PNG (RGB -> BGR for OpenCV)
                    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
                    cv2.imwrite(str(out_path), bgr)
                    return str(out_path)
            except Exception as err:
                logger.warning(f"Rasterio preview generation failed: {err}. Trying PIL.")

        # Fallback to PIL
        with Image.open(src_path) as img:
            rgb_img = img.convert("RGB")
            rgb_img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
            rgb_img.save(str(out_path), format="PNG")
            return str(out_path)
