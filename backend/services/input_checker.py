"""
SatQuery AI — Input Compatibility Checker

Validates modality, image count, format (GeoTIFF/TIFF vs. benchmark PNG/JPEG),
co-registration/pairing, and basic metadata (dimensions, bands) before anything
touches a model.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
from PIL import Image

from backend.config import SUPPORTED_IMAGE_FORMATS, GEOTIFF_FORMATS, BENCHMARK_FORMATS


def detect_modality(file_path: str, user_hint: str = "") -> str:
    """
    Detect image modality from file metadata / user hint.
    Returns: 'optical', 'sar', 'multispectral', or 'unknown'.
    """
    try:
        from backend.services.fusion_service import OpticalSARFusionService
        detected = OpticalSARFusionService.detect_modality(file_path, user_hint)
        if detected in ("sar", "optical"):
            # Check if multispectral (4+ bands)
            try:
                with Image.open(file_path) as img:
                    if len(img.getbands()) >= 4:
                        return "multispectral"
            except Exception:
                pass
            return detected
    except Exception:
        pass

    hint_lower = user_hint.lower()
    if "sar" in hint_lower or "radar" in hint_lower or "sentinel-1" in hint_lower or "risat" in hint_lower:
        return "sar"
    if "multispectral" in hint_lower or "sentinel-2" in hint_lower:
        return "multispectral"
    if "optical" in hint_lower or "rgb" in hint_lower or "cartosat" in hint_lower:
        return "optical"

    # Infer from file characteristics
    ext = Path(file_path).suffix.lower()
    if ext in BENCHMARK_FORMATS:
        return "optical"  # PNG/JPEG are typically optical

    try:
        with Image.open(file_path) as img:
            bands = len(img.getbands())
            if bands == 1:
                return "sar"  # Single-band likely SAR amplitude
            elif bands == 3:
                return "optical"
            elif bands >= 4:
                return "multispectral"
    except Exception:
        pass

    return "unknown"



def extract_metadata(file_path: str) -> dict:
    """Extract basic image metadata using Rasterio for GeoTIFFs and Pillow for standard images."""
    meta = {
        "file_name": os.path.basename(file_path),
        "file_size_bytes": os.path.getsize(file_path),
        "format": Path(file_path).suffix.lower().lstrip("."),
    }

    # 1. Try Rasterio first (handles arbitrary band counts, float32, and complex GeoTIFF headers)
    try:
        import rasterio
        with rasterio.open(file_path) as src:
            meta["width"] = src.width
            meta["height"] = src.height
            meta["bands"] = src.count
            meta["band_names"] = [d or f"Band_{i+1}" for i, d in enumerate(src.descriptions or [])]
            if not meta["band_names"]:
                meta["band_names"] = [f"Band_{i+1}" for i in range(src.count)]
            meta["mode"] = f"{src.dtypes[0]}_{src.count}band"
            meta["is_georeferenced"] = bool(src.crs)
            if src.crs:
                meta["crs"] = str(src.crs)
            meta["geotiff_tags"] = {str(k): str(v) for k, v in src.tags().items()}
            return meta
    except Exception:
        pass

    # 2. Fallback to Pillow for standard PNG/JPEG
    try:
        with Image.open(file_path) as img:
            meta["width"] = img.width
            meta["height"] = img.height
            meta["bands"] = len(img.getbands())
            meta["band_names"] = list(img.getbands())
            meta["mode"] = img.mode

            # Check for GeoTIFF tags
            if hasattr(img, "tag_v2"):
                geo_keys = {
                    33922: "model_tiepoint",
                    33550: "model_pixel_scale",
                    34735: "geo_key_directory",
                    34736: "geo_double_params",
                    34737: "geo_ascii_params",
                }
                geo_meta = {}
                for tag_id, name in geo_keys.items():
                    if tag_id in img.tag_v2:
                        geo_meta[name] = str(img.tag_v2[tag_id])
                if geo_meta:
                    meta["geotiff_tags"] = geo_meta
                    meta["is_georeferenced"] = True
                else:
                    meta["is_georeferenced"] = False
            else:
                meta["is_georeferenced"] = False
    except Exception as e:
        meta["error"] = f"Could not read image: {str(e)}"

    return meta



def validate_format(file_path: str) -> tuple[bool, str]:
    """Check if file format is supported."""
    ext = Path(file_path).suffix.lower()
    if ext not in SUPPORTED_IMAGE_FORMATS:
        return False, f"Unsupported format '{ext}'. Supported: {', '.join(sorted(SUPPORTED_IMAGE_FORMATS))}"
    return True, "ok"


def validate_single_image(file_path: str, modality_hint: str = "") -> dict:
    """
    Validate a single image for analysis.
    Returns a validation result dict.
    """
    result = {
        "valid": False,
        "input_type": "single_image",
        "file_path": file_path,
        "errors": [],
        "warnings": [],
        "metadata": {},
    }

    # Check file exists
    if not os.path.isfile(file_path):
        result["errors"].append(f"File not found: {file_path}")
        return result

    # Check format
    fmt_ok, fmt_msg = validate_format(file_path)
    if not fmt_ok:
        result["errors"].append(fmt_msg)
        return result

    # Extract metadata
    meta = extract_metadata(file_path)
    result["metadata"] = meta

    if "error" in meta:
        result["errors"].append(meta["error"])
        return result

    # Detect modality
    modality = detect_modality(file_path, modality_hint)
    result["modality"] = modality
    result["metadata"]["detected_modality"] = modality

    if modality == "unknown":
        result["warnings"].append("Could not auto-detect modality. Assuming optical.")
        result["modality"] = "optical"

    # Check minimum dimensions
    if meta.get("width", 0) < 16 or meta.get("height", 0) < 16:
        result["errors"].append(f"Image too small: {meta.get('width')}×{meta.get('height')}. Minimum 16×16.")
        return result

    result["valid"] = True
    return result


def validate_image_pair(
    file_path_1: str,
    file_path_2: str,
    pair_type: str = "bi_temporal",
    modality_hint_1: str = "",
    modality_hint_2: str = "",
) -> dict:
    """
    Validate a pair of images (bi-temporal or optical+SAR).
    pair_type: 'bi_temporal' or 'optical_sar'
    """
    result = {
        "valid": False,
        "input_type": f"{pair_type}_pair",
        "errors": [],
        "warnings": [],
        "images": [],
    }

    # Validate each image individually
    v1 = validate_single_image(file_path_1, modality_hint_1)
    v2 = validate_single_image(file_path_2, modality_hint_2)
    result["images"] = [v1, v2]

    if not v1["valid"]:
        result["errors"].append(f"Image 1 invalid: {'; '.join(v1['errors'])}")
    if not v2["valid"]:
        result["errors"].append(f"Image 2 invalid: {'; '.join(v2['errors'])}")

    if result["errors"]:
        return result

    # Pair-type-specific checks
    if pair_type == "optical_sar":
        m1 = v1.get("modality", "unknown")
        m2 = v2.get("modality", "unknown")
        modalities = {m1, m2}
        if not ({"optical", "sar"} <= modalities or {"multispectral", "sar"} <= modalities):
            result["errors"].append(
                f"Optical–SAR pair requires one optical/multispectral and one SAR image. "
                f"Got: {m1} and {m2}."
            )
            return result

    elif pair_type == "bi_temporal":
        # Both should be same modality
        m1 = v1.get("modality", "unknown")
        m2 = v2.get("modality", "unknown")
        if m1 != m2:
            result["warnings"].append(
                f"Bi-temporal pair has mismatched modalities ({m1} vs {m2}). "
                f"Results may be unreliable."
            )

    # Check dimension compatibility (rough co-registration check)
    w1 = v1["metadata"].get("width", 0)
    h1 = v1["metadata"].get("height", 0)
    w2 = v2["metadata"].get("width", 0)
    h2 = v2["metadata"].get("height", 0)

    if w1 > 0 and w2 > 0:
        dim_ratio = max(w1, w2) / max(min(w1, w2), 1)
        if dim_ratio > 4:
            result["warnings"].append(
                f"Large dimension mismatch ({w1}×{h1} vs {w2}×{h2}). "
                f"Images may not be co-registered."
            )

    result["valid"] = True
    return result


def check_compatibility(file_paths: list[str], modality_hints: list[str] | None = None) -> dict:
    """
    Top-level compatibility check for any input configuration.
    Determines input type and validates accordingly.
    """
    hints = modality_hints or [""] * len(file_paths)

    n = len(file_paths)

    if n == 0:
        return {
            "valid": False,
            "input_type": "none",
            "errors": ["No images provided."],
            "warnings": [],
        }

    if n == 1:
        return validate_single_image(file_paths[0], hints[0])

    if n == 2:
        # Detect if optical+SAR pair or bi-temporal
        m1 = detect_modality(file_paths[0], hints[0])
        m2 = detect_modality(file_paths[1], hints[1])

        if {m1, m2} == {"optical", "sar"} or {m1, m2} == {"multispectral", "sar"}:
            return validate_image_pair(
                file_paths[0], file_paths[1],
                pair_type="optical_sar",
                modality_hint_1=hints[0],
                modality_hint_2=hints[1],
            )
        else:
            return validate_image_pair(
                file_paths[0], file_paths[1],
                pair_type="bi_temporal",
                modality_hint_1=hints[0],
                modality_hint_2=hints[1],
            )

    # More than 2 images
    return {
        "valid": False,
        "input_type": "unsupported",
        "errors": [f"Too many images ({n}). Maximum is 2 (a single image or a co-registered pair)."],
        "warnings": [],
    }
