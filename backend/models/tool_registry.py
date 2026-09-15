"""
SatQuery AI — Tool / Model Registry

JSON-schema-based registry of specialist models. Each tool entry defines:
  tool_id, task_type, accepts (input_type, modality, formats), parameters, outputs.

The controller selects from this registry — it cannot invent tools or parameters
outside the schema. This makes the execution trace (Section 6 of the build guide)
trivial to produce.
"""

from __future__ import annotations
from typing import Optional

TOOL_REGISTRY: list[dict] = [
    # ── Single-Image VQA ────────────────────────────────
    {
        "tool_id": "rs_vqa_v1",
        "task_type": "vqa",
        "display_name": "Remote Sensing VQA",
        "description": "Answers natural-language questions about a single remote sensing image (presence, count, color, shape, position, comparison, reasoning).",
        "accepts": {
            "input_type": "single_image",
            "modality": ["optical", "sar", "multispectral"],
            "formats": ["GeoTIFF", "TIFF", "PNG", "JPEG"],
        },
        "parameters": {
            "question_type": [
                "presence", "comparison", "count", "color",
                "shape", "size", "position", "direction",
                "scene", "reasoning",
            ],
        },
        "outputs": ["answer_text", "confidence"],
        "reference_model": "GeoChat / RS-adapted LLaVA",
        "evaluation_benchmarks": ["RSVQA-LR", "RSVQA-HR", "VRSBench-VQA"],
    },

    # ── Single-Image Grounding ──────────────────────────
    {
        "tool_id": "rs_grounding_v1",
        "task_type": "grounding",
        "display_name": "Remote Sensing Grounding",
        "description": "Localizes objects/regions in a remote sensing image given a text description, producing bounding boxes.",
        "accepts": {
            "input_type": "single_image",
            "modality": ["optical", "multispectral"],
            "formats": ["GeoTIFF", "TIFF", "PNG", "JPEG"],
        },
        "parameters": {
            "target_description": "free_text",
            "max_detections": 10,
        },
        "outputs": ["bounding_boxes", "labels", "confidence"],
        "reference_model": "GeoChat coordinate-token grounding",
        "evaluation_benchmarks": ["VRSBench-Referring"],
    },

    # ── Single-Image Captioning ─────────────────────────
    {
        "tool_id": "rs_caption_v1",
        "task_type": "captioning",
        "display_name": "Remote Sensing Captioning",
        "description": "Generates a detailed natural-language description of a remote sensing image.",
        "accepts": {
            "input_type": "single_image",
            "modality": ["optical", "multispectral"],
            "formats": ["GeoTIFF", "TIFF", "PNG", "JPEG"],
        },
        "parameters": {
            "detail_level": ["brief", "detailed"],
        },
        "outputs": ["caption_text", "confidence"],
        "reference_model": "RS-adapted VLM decoder",
        "evaluation_benchmarks": ["VRSBench-Cap"],
    },

    # ── Bi-Temporal Change VQA ──────────────────────────
    {
        "tool_id": "cdvqa_change_v1",
        "task_type": "change_vqa",
        "display_name": "Change Detection VQA",
        "description": "Answers questions about changes between two temporally separated images of the same area.",
        "accepts": {
            "input_type": "bi_temporal_pair",
            "modality": ["optical"],
            "formats": ["GeoTIFF", "TIFF", "PNG", "JPEG"],
        },
        "parameters": {
            "question_type": ["binary", "trend", "class_transition", "count_change"],
        },
        "outputs": ["answer_text", "change_map_optional", "confidence"],
        "reference_model": "Siamese encoder + CDVQA decoder",
        "evaluation_benchmarks": ["CDVQA"],
    },

    # ── Optical–SAR Fusion Analysis ─────────────────────
    {
        "tool_id": "optical_sar_fusion_v1",
        "task_type": "fusion",
        "display_name": "Optical-SAR Fusion Analysis",
        "description": "Joint analysis of co-registered optical and SAR image pairs for built-up area, water body, and land cover extraction.",
        "accepts": {
            "input_type": "optical_sar_pair",
            "modality": ["optical+sar"],
            "formats": ["GeoTIFF", "TIFF", "PNG", "JPEG"],
        },
        "parameters": {
            "target_classes": ["built_up", "water", "vegetation", "bare_soil"],
            "fusion_mode": ["early", "deep", "late"],
        },
        "outputs": ["classification_map", "class_labels", "answer_text", "confidence"],
        "reference_model": "OpticalSARFusionNet / Dual-branch cross-gated fusion",
        "evaluation_benchmarks": ["BigEarthNet-MM benchmark split"],
    },

]


def get_registry() -> list[dict]:
    """Return the full tool registry."""
    return TOOL_REGISTRY


def get_tool(tool_id: str) -> Optional[dict]:
    """Look up a single tool by ID."""
    for tool in TOOL_REGISTRY:
        if tool["tool_id"] == tool_id:
            return tool
    return None


def get_tools_for_task(task_type: str) -> list[dict]:
    """Return all tools that handle a given task type."""
    return [t for t in TOOL_REGISTRY if t["task_type"] == task_type]


def get_tool_summary() -> list[dict]:
    """Compact summary for the /api/tools endpoint."""
    return [
        {
            "tool_id": t["tool_id"],
            "task_type": t["task_type"],
            "display_name": t["display_name"],
            "description": t["description"],
            "accepts": t["accepts"],
            "outputs": t["outputs"],
        }
        for t in TOOL_REGISTRY
    ]
