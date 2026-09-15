"""
SatQuery AI — Agent Model & Tool Registry

JSON-schema based registry of remote sensing specialist tools.
Defines tasks, permitted input formats, modalities, schema parameters, and benchmark splits.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ToolSchema(BaseModel):
    tool_id: str
    task_type: str
    display_name: str
    description: str
    accepts: Dict[str, Any]
    parameters: Dict[str, Any]
    outputs: List[str]
    reference_model: str
    evaluation_benchmarks: List[str]


MODEL_TOOL_REGISTRY: List[ToolSchema] = [
    ToolSchema(
        tool_id="rs_vqa_v1",
        task_type="vqa",
        display_name="Remote Sensing VQA Specialist",
        description="Answers natural-language questions about single remote sensing imagery (presence, count, color, shape, comparison, spatial reasoning).",
        accepts={
            "input_type": "single_image",
            "modality": ["optical", "sar", "multispectral"],
            "formats": ["GeoTIFF", "TIFF", "PNG", "JPEG"],
        },
        parameters={
            "question_type": [
                "presence", "comparison", "count", "color",
                "shape", "size", "position", "direction", "scene", "reasoning"
            ]
        },
        outputs=["answer_text", "confidence", "visual_evidence"],
        reference_model="GeoChat / RS-adapted LLaVA",
        evaluation_benchmarks=["RSVQA-LR", "RSVQA-HR", "VRSBench-VQA"],
    ),
    ToolSchema(
        tool_id="rs_captioning_v1",
        task_type="captioning",
        display_name="Remote Sensing Captioning Specialist",
        description="Generates detailed, geographically grounded descriptive captions for a single remote sensing image.",
        accepts={
            "input_type": "single_image",
            "modality": ["optical", "multispectral", "sar"],
            "formats": ["GeoTIFF", "TIFF", "PNG", "JPEG"],
        },
        parameters={
            "detail_level": ["concise", "detailed", "attribute_focused"],
            "include_orientation": [True, False],
        },
        outputs=["caption_text", "confidence", "detected_classes"],
        reference_model="RemoteCLIP / VRSBench Captioner",
        evaluation_benchmarks=["VRSBench-Caption"],
    ),
    ToolSchema(
        tool_id="rs_grounding_v1",
        task_type="grounding",
        display_name="Remote Sensing Grounding Specialist",
        description="Localizes objects or geographic regions specified by natural language, returning bounding boxes.",
        accepts={
            "input_type": "single_image",
            "modality": ["optical", "multispectral"],
            "formats": ["GeoTIFF", "TIFF", "PNG", "JPEG"],
        },
        parameters={
            "target_description": "free_text",
            "max_detections": 10,
        },
        outputs=["bounding_boxes", "labels", "confidence"],
        reference_model="GeoChat coordinate-token grounding",
        evaluation_benchmarks=["VRSBench-Referring"],
    ),
    ToolSchema(
        tool_id="rs_change_v1",
        task_type="change_detection",
        display_name="Bi-Temporal Change Specialist",
        description="Detects, maps, and explains environmental/structural changes between two co-registered scenes.",
        accepts={
            "input_type": "bi_temporal_pair",
            "modality": ["optical", "sar"],
            "formats": ["GeoTIFF", "TIFF", "PNG", "JPEG"],
        },
        parameters={
            "output_format": ["change_map", "change_mask", "qa_answer", "narrative"],
            "change_classes": ["buildings", "vegetation", "water", "roads", "all"],
        },
        outputs=["change_map_url", "changed_regions", "change_description", "confidence"],
        reference_model="ChangeFormer / BIT / CDVQA Specialist",
        evaluation_benchmarks=["CDVQA", "SECOND Change Benchmark"],
    ),
    ToolSchema(
        tool_id="rs_fusion_v1",
        task_type="optical_sar_fusion",
        display_name="Optical-SAR Cross-Modal Specialist",
        description="Jointly extracts information from a co-registered optical and SAR image pair.",
        accepts={
            "input_type": "optical_sar_pair",
            "modality": ["optical+sar"],
            "formats": ["GeoTIFF", "TIFF", "PNG", "JPEG"],
        },
        parameters={
            "query_focus": ["all_weather_presence", "texture_clarification", "terrain_penetration"],
        },
        outputs=["joint_answer", "modality_contributions", "confidence"],
        reference_model="Cross-Modal Attention Fusion (BigEarthNet.txt adapted)",
        evaluation_benchmarks=["BigEarthNet.txt Benchmark", "ISRO/SAC Cartosat-2S+RISAT"],
    ),
]


def get_tool_by_id(tool_id: str) -> Optional[ToolSchema]:
    for tool in MODEL_TOOL_REGISTRY:
        if tool.tool_id == tool_id:
            return tool
    return None


def get_tools_for_task(task_type: str) -> List[ToolSchema]:
    return [t for t in MODEL_TOOL_REGISTRY if t.task_type == task_type]
