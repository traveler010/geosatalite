"""
SatQuery AI — Agent Input Compatibility Validator

Validates image count, modalities, pairing rules, and file formats
before any request reaches a specialist model.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from backend.core.errors import InputCompatibilityError
from backend.core.logging import get_logger

logger = get_logger("agent.validator")


class InputValidator:
    """Validates remote sensing inputs against tool requirements."""

    @classmethod
    def validate_inputs(
        cls,
        task_type: str,
        images_metadata: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Validate input image count, modalities, and formats.
        Raises InputCompatibilityError on mismatch.
        """
        image_count = len(images_metadata)

        if image_count == 0:
            raise InputCompatibilityError(
                "No image provided. Please upload at least one satellite image or GeoTIFF.",
                details={"required_count": 1, "received_count": 0},
            )

        modalities = [meta.get("modality", "optical").lower() for meta in images_metadata]
        formats = [meta.get("format", "PNG").upper() for meta in images_metadata]

        # 1. Single-Image Tasks (VQA, Captioning, Grounding)
        if task_type in ("vqa", "captioning", "grounding"):
            if image_count > 1:
                logger.info(f"Task '{task_type}' operates on single image. Using primary image (1 of {image_count}).")
            return {
                "valid": True,
                "workflow_type": "single_image",
                "image_count": 1,
                "modality": modalities[0],
                "format": formats[0],
            }

        # 2. Bi-Temporal Change Detection
        if task_type == "change_detection":
            if image_count < 2:
                raise InputCompatibilityError(
                    f"Task '{task_type}' requires 2 co-registered temporal images (Image T1 and Image T2). Only received {image_count}.",
                    details={"task": task_type, "required": 2, "received": image_count},
                )
            # Modality check: optical-optical or SAR-SAR
            m1, m2 = modalities[0], modalities[1]
            if (m1 == "sar" and m2 != "sar") or (m1 != "sar" and m2 == "sar"):
                raise InputCompatibilityError(
                    f"Bi-temporal change detection requires matching sensor modalities. Received '{m1}' and '{m2}'. "
                    "For cross-modal optical+SAR analysis, use the Optical-SAR Fusion workflow.",
                    details={"image_1_modality": m1, "image_2_modality": m2},
                )
            return {
                "valid": True,
                "workflow_type": "bi_temporal_pair",
                "image_count": 2,
                "modality": m1,
                "formats": formats[:2],
            }

        # 3. Optical-SAR Cross-Modal Fusion
        if task_type == "optical_sar_fusion":
            if image_count < 2:
                raise InputCompatibilityError(
                    f"Optical-SAR fusion requires exactly 2 co-registered images (1 Optical/Multispectral + 1 SAR). Received {image_count}.",
                    details={"task": task_type, "required": 2, "received": image_count},
                )
            has_optical = any(m in ("optical", "multispectral") for m in modalities[:2])
            has_sar = any(m == "sar" for m in modalities[:2])
            if not (has_optical and has_sar):
                raise InputCompatibilityError(
                    f"Optical-SAR fusion requires one optical image and one SAR radar image. Received: {modalities[:2]}.",
                    details={"modalities": modalities[:2]},
                )
            return {
                "valid": True,
                "workflow_type": "optical_sar_pair",
                "image_count": 2,
                "modality": "optical+sar",
                "formats": formats[:2],
            }

        # Default pass-through
        return {
            "valid": True,
            "workflow_type": "generic",
            "image_count": image_count,
            "modalities": modalities,
        }
