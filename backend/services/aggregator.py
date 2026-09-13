"""
SatQuery AI — Output Aggregator & Confidence Estimator

Merges textual and spatial outputs from specialist models,
computes confidence scores, and structures the combined evidence.
"""

from __future__ import annotations
from typing import Any


def aggregate_outputs(raw_result: dict, task_type: str) -> dict:
    """
    Merge and normalize specialist outputs into a unified response structure.
    """
    aggregated = {
        "answer": None,
        "evidence": {},
    }

    if task_type == "vqa":
        aggregated["answer"] = raw_result.get("answer", "No answer generated.")
        aggregated["evidence"] = {
            "question_type": raw_result.get("question_type", "unknown"),
        }

    elif task_type == "grounding":
        boxes = raw_result.get("bounding_boxes", [])
        n = raw_result.get("num_detections", len(boxes))
        aggregated["answer"] = f"Detected {n} region(s) matching the query."
        aggregated["evidence"] = {
            "bounding_boxes": boxes,
            "num_detections": n,
        }

    elif task_type == "captioning":
        aggregated["answer"] = None  # Use caption field instead
        aggregated["caption"] = raw_result.get("caption", "No caption generated.")
        aggregated["evidence"] = {
            "detail_level": raw_result.get("detail_level", "detailed"),
        }

    elif task_type == "change_vqa":
        aggregated["answer"] = raw_result.get("answer", "No change analysis generated.")
        aggregated["evidence"] = {
            "question_type": raw_result.get("question_type", "unknown"),
            "change_map_ref": raw_result.get("change_map_ref"),
        }

    elif task_type == "fusion":
        aggregated["answer"] = raw_result.get("answer", "No fusion analysis generated.")
        aggregated["evidence"] = {
            "class_distribution": raw_result.get("class_distribution", {}),
            "fusion_mode": raw_result.get("fusion_mode", "early"),
        }

    else:
        aggregated["answer"] = raw_result.get("answer", "Analysis complete.")

    return aggregated


def estimate_confidence(raw_result: dict) -> float:
    """
    Estimate output confidence.

    Strategy (from Section 6 of the build guide):
      (a) softmax margin / top-1-vs-top-2 gap from the specialist — free and defensible
      (b) ensemble agreement (future)
      (c) calibration head (future)

    Currently uses approach (a): direct confidence from the specialist model.
    """
    conf = raw_result.get("confidence", 0.0)

    # If we have bounding boxes, average their confidences
    if "bounding_boxes" in raw_result:
        boxes = raw_result["bounding_boxes"]
        if boxes:
            box_confs = [b.get("confidence", 0.0) for b in boxes]
            conf = sum(box_confs) / len(box_confs)

    # Clamp to [0, 1]
    return round(max(0.0, min(1.0, conf)), 3)


def confidence_level(confidence: float) -> str:
    """Map confidence score to a human-readable level."""
    if confidence >= 0.80:
        return "high"
    elif confidence >= 0.55:
        return "medium"
    else:
        return "low"
