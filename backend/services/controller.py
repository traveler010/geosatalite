"""
SatQuery AI — Agentic Controller

The core orchestrator that:
  1. Interprets the query and classifies the task
  2. Calls the Input Compatibility Checker
  3. Selects tool(s) from the registry
  4. Configures permitted parameters
  5. Executes specialist model(s)
  6. Returns structured result with execution trace

Designed as a constrained function-calling loop — the controller can only
select tools and parameters defined in the registry schema.
"""

from __future__ import annotations

import re
import uuid
import time
from typing import Optional

from backend.models.tool_registry import get_tools_for_task, get_tool
from backend.models.specialists import get_specialist
from backend.services.input_checker import check_compatibility
from backend.services.aggregator import aggregate_outputs, estimate_confidence
from backend.services.trace_builder import build_trace


# ─── Task Classification ────────────────────────────────

# Keyword patterns for intent detection
_TASK_PATTERNS = {
    "change_vqa": [
        r"\bchang(e|ed|es|ing)\b", r"\bbefore\s+(and|&)\s+after\b",
        r"\btempora(l|lly)\b", r"\bincreas(e|ed)\b.*\b(area|cover)",
        r"\bdecreas(e|ed)\b.*\b(area|cover)", r"\btransition\b",
        r"\bgrown?\b", r"\bexpand(ed)?\b", r"\bshrunk?\b",
        r"\bcompare\b.*\b(image|photo|scene)s?\b",
    ],
    "fusion": [
        r"\boptical\b.*\bsar\b", r"\bsar\b.*\boptical\b",
        r"\bfus(e|ion)\b", r"\bcross[\s-]?modal\b",
        r"\bjoint\b.*\b(analy|extract|identif)",
        r"\bsentinel[\s-]?1\b.*\bsentinel[\s-]?2\b",
        r"\bradar\b.*\boptical\b", r"\bmulti[\s-]?sensor\b",
        r"\bbuilt[\s-]?up\b.*\bwater\b",
    ],
    "grounding": [
        r"\blocali[sz]e\b", r"\bfind\b.*\b(where|location|position)\b",
        r"\bhighlight\b", r"\boutline\b", r"\bbox(es)?\b",
        r"\bbound(ing)?\b", r"\bmark\b.*\b(area|region|object)\b",
        r"\bdetect\b.*\b(and|&)\b.*\b(show|mark|locate)\b",
        r"\bwhere\s+(is|are)\b", r"\bpoint\s+out\b",
        r"\bshow\s+me\b", r"\bidentify\s+and\s+locate\b",
    ],
    "captioning": [
        r"\bdescri(be|ption)\b", r"\bcaption\b",
        r"\bwhat\s+(is|does)\s+this\s+(image|scene|area)\s+(show|depict|contain)\b",
        r"\bsummari[sz]e\b.*\b(image|scene)\b",
        r"\btell\s+me\s+about\b",
    ],
    "vqa": [
        # Catch-all for questions — VQA is the default for single-image queries
        r"\bhow\s+many\b", r"\bis\s+there\b", r"\bare\s+there\b",
        r"\bwhat\s+(is|are|color|type|kind)\b", r"\bcount\b",
        r"\bpresence\b", r"\bwhich\b", r"\bdo(es)?\s+the\b",
    ],
}

_QUESTION_TYPE_PATTERNS = {
    "presence": [r"\bis\s+there\b", r"\bare\s+there\b", r"\bpresence\b", r"\bvisible\b", r"\bexist\b"],
    "count": [r"\bhow\s+many\b", r"\bcount\b", r"\bnumber\s+of\b"],
    "comparison": [r"\blarger\b", r"\bsmaller\b", r"\bmore\b", r"\bless\b", r"\bcompar\b", r"\bbigger\b"],
    "color": [r"\bcolor\b", r"\bcolour\b", r"\bappear(s|ance)?\b"],
    "position": [r"\bwhere\b", r"\blocation\b", r"\bposition\b", r"\bquadrant\b"],
    "scene": [r"\bscene\b", r"\btype\s+of\s+(area|land|region)\b", r"\blandscape\b"],
    "reasoning": [r"\bwhy\b", r"\bexplain\b", r"\breason\b", r"\bbecause\b", r"\bcause\b"],
}

_CHANGE_QUESTION_PATTERNS = {
    "binary": [r"\bhas\b.*\bchanged\b", r"\bany\s+change\b", r"\bsame\b", r"\bunchanged\b"],
    "trend": [r"\bincreas\b", r"\bdecreas\b", r"\bgrow\b", r"\bexpand\b", r"\bshrink\b", r"\btrend\b"],
    "class_transition": [r"\bconvert\b", r"\btransition\b", r"\btransform\b", r"\bbecome\b", r"\bturn(ed)?\s+into\b"],
    "count_change": [r"\bhow\s+many\b.*\bchang\b", r"\bnumber\b.*\bchang\b"],
}


def classify_task(query: str, input_type: str) -> str:
    """
    Classify the requested task from the query text and input configuration.
    Returns a task_type string matching the tool registry.
    """
    q_lower = query.lower()

    # Input type strongly constrains the task
    if input_type == "optical_sar_pair":
        return "fusion"

    if input_type == "bi_temporal_pair":
        return "change_vqa"

    # For single images, classify from query text
    for task_type, patterns in _TASK_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, q_lower):
                return task_type

    # Default: VQA for questions, captioning for descriptive requests
    if q_lower.strip().endswith("?") or any(w in q_lower for w in ["how", "what", "where", "is", "are", "which", "do"]):
        return "vqa"

    return "captioning"


def classify_question_type(query: str, task_type: str) -> str:
    """Classify the question sub-type for VQA or change_vqa tasks."""
    q_lower = query.lower()

    if task_type == "change_vqa":
        patterns = _CHANGE_QUESTION_PATTERNS
        default = "trend"
    else:
        patterns = _QUESTION_TYPE_PATTERNS
        default = "scene"

    for qtype, pats in patterns.items():
        for pat in pats:
            if re.search(pat, q_lower):
                return qtype

    return default


# ─── Main Controller ────────────────────────────────────

def execute_query(
    query: str,
    file_paths: list[str],
    modality_hints: list[str] | None = None,
    location: dict | None = None,
) -> dict:
    """
    Run the full agentic pipeline:
      query → compatibility check → task classification → tool selection
      → specialist execution → aggregation → trace building

    Returns a dict with: answer, evidence, trace, confidence, query_id
    """
    query_id = str(uuid.uuid4())[:12]
    start_time = time.time()
    errors = []

    # ── Step 1: Input Compatibility Check ─────────────
    if file_paths:
        compatibility = check_compatibility(file_paths, modality_hints)
    else:
        # No images — text-only query (general Q&A mode)
        compatibility = {
            "valid": True,
            "input_type": "text_only",
            "errors": [],
            "warnings": [],
            "metadata": {},
            "modality": "none",
        }

    if not compatibility["valid"]:
        return {
            "query_id": query_id,
            "success": False,
            "error": "Input validation failed",
            "validation_errors": compatibility["errors"],
            "compatibility": compatibility,
            "trace": build_trace(
                query_id=query_id,
                query=query,
                input_summary=compatibility,
                task_type=None,
                tool_id=None,
                parameters={},
                result=None,
                confidence=0.0,
                duration=time.time() - start_time,
                error="Input validation failed: " + "; ".join(compatibility["errors"]),
            ),
        }

    input_type = compatibility.get("input_type", "single_image")

    # ── Step 2: Task Classification ───────────────────
    task_type = classify_task(query, input_type)
    question_type = classify_question_type(query, task_type)

    # ── Step 3: Tool Selection ────────────────────────
    available_tools = get_tools_for_task(task_type)
    if not available_tools:
        return {
            "query_id": query_id,
            "success": False,
            "error": f"No tool available for task type: {task_type}",
            "trace": build_trace(
                query_id=query_id,
                query=query,
                input_summary=compatibility,
                task_type=task_type,
                tool_id=None,
                parameters={"question_type": question_type},
                result=None,
                confidence=0.0,
                duration=time.time() - start_time,
                error=f"No tool for task: {task_type}",
            ),
        }

    selected_tool = available_tools[0]  # Pick the first (best) match
    tool_id = selected_tool["tool_id"]

    # ── Step 4: Configure Parameters ──────────────────
    parameters = {"question_type": question_type}

    if task_type == "grounding":
        parameters["target_description"] = query

    if task_type == "captioning":
        parameters["detail_level"] = "detailed"

    if task_type == "fusion":
        parameters["target_classes"] = selected_tool["parameters"].get("target_classes", [])
        parameters["fusion_mode"] = "early"

    # ── Step 5: Execute Specialist ────────────────────
    try:
        specialist = get_specialist(task_type)

        if task_type == "vqa":
            raw_result = specialist.predict(
                image_path=file_paths[0] if file_paths else "demo_image",
                question=query,
                question_type=question_type,
            )
        elif task_type == "grounding":
            raw_result = specialist.predict(
                image_path=file_paths[0] if file_paths else "demo_image",
                description=query,
            )
        elif task_type == "captioning":
            raw_result = specialist.predict(
                image_path=file_paths[0] if file_paths else "demo_image",
                detail_level="detailed",
            )
        elif task_type == "change_vqa":
            raw_result = specialist.predict(
                image_path_t1=file_paths[0] if len(file_paths) > 0 else "demo_t1",
                image_path_t2=file_paths[1] if len(file_paths) > 1 else "demo_t2",
                question=query,
                question_type=question_type,
            )
        elif task_type == "fusion":
            raw_result = specialist.predict(
                optical_path=file_paths[0] if len(file_paths) > 0 else "demo_optical",
                sar_path=file_paths[1] if len(file_paths) > 1 else "demo_sar",
                target_classes=parameters.get("target_classes"),
            )
        else:
            raw_result = {"answer": "Unsupported task.", "confidence": 0.0}

    except Exception as e:
        raw_result = {"answer": f"Inference error: {str(e)}", "confidence": 0.0}
        errors.append(str(e))

    # ── Step 6: Aggregate & Build Trace ───────────────
    aggregated = aggregate_outputs(raw_result, task_type)
    confidence = estimate_confidence(raw_result)
    duration = time.time() - start_time

    # Build the input summary for the trace
    input_summary = {
        "type": input_type,
        "modality": compatibility.get("modality", "unknown"),
        "format": compatibility.get("metadata", {}).get("format", "unknown"),
        "n_images": len(file_paths),
    }

    trace = build_trace(
        query_id=query_id,
        query=query,
        input_summary=input_summary,
        task_type=task_type,
        tool_id=tool_id,
        parameters=parameters,
        result=aggregated,
        confidence=confidence,
        duration=duration,
        error="; ".join(errors) if errors else None,
    )

    # Compose the answer text
    answer_text = aggregated.get("answer") or aggregated.get("caption") or "Analysis complete."

    return {
        "query_id": query_id,
        "success": True,
        "answer": answer_text,
        "confidence": confidence,
        "task_type": task_type,
        "tool_used": tool_id,
        "evidence": aggregated.get("evidence", {}),
        "raw_result": aggregated,
        "trace": trace,
        "compatibility": compatibility,
        "processing_time_ms": round(duration * 1000, 1),
    }
