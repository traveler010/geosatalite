"""
SatQuery AI — Agent Router

Interprets natural language query intent, evaluates input image count/modality,
and selects the target remote sensing workflow.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from backend.core.logging import get_logger

logger = get_logger("agent.router")


class AgentRouter:
    """Classifies user queries into remote sensing tasks."""

    CHANGE_KEYWORDS = [
        "change", "changed", "difference", "diff", "temporal", "between",
        "before and after", "t1", "t2", "evolution", "growth", "shrink",
        "deforestation", "construction", "loss", "recovery", "expansion"
    ]

    FUSION_KEYWORDS = [
        "fusion", "optical and sar", "sar and optical", "joint", "radar and optical",
        "penetration", "all-weather", "cross-modal", "complementary", "fused"
    ]

    GROUNDING_KEYWORDS = [
        "locate", "find", "ground", "where is", "where are", "bounding box",
        "bbox", "detect", "point out", "coordinates of", "highlight", "mark"
    ]

    CAPTIONING_KEYWORDS = [
        "describe", "caption", "tell me about", "what is in this", "summary",
        "scene description", "overview", "give an overview", "explain this image"
    ]

    @classmethod
    def route_task(
        cls,
        query: str,
        image_count: int = 1,
        modalities: Optional[List[str]] = None,
    ) -> str:
        """
        Classify intent based on text semantics and input characteristics.
        Returns one of: 'vqa', 'captioning', 'grounding', 'change_detection', 'optical_sar_fusion'.
        """
        q = query.strip().lower()
        mods = [m.lower() for m in (modalities or [])]

        # Explicit optical-SAR input
        if image_count >= 2 and ("optical" in mods and "sar" in mods):
            logger.info("Routing to 'optical_sar_fusion' based on optical+SAR image inputs.")
            return "optical_sar_fusion"

        # Explicit 2-image input matching modalities
        if image_count >= 2 and any(k in q for k in cls.CHANGE_KEYWORDS):
            logger.info("Routing to 'change_detection' based on temporal pair & keywords.")
            return "change_detection"

        # Text keyword checks
        if any(re.search(rf"\b{re.escape(k)}\b", q) for k in cls.FUSION_KEYWORDS):
            return "optical_sar_fusion"

        if any(re.search(rf"\b{re.escape(k)}\b", q) for k in cls.CHANGE_KEYWORDS) and image_count >= 2:
            return "change_detection"

        if any(re.search(rf"\b{re.escape(k)}\b", q) for k in cls.GROUNDING_KEYWORDS):
            return "grounding"

        if any(re.search(rf"\b{re.escape(k)}\b", q) for k in cls.CAPTIONING_KEYWORDS):
            return "captioning"

        # Default single-image VQA
        return "vqa"
