"""
SatQuery AI — Execution Trace Builder

Produces the auditable JSON execution summary that gets graded:
  task, model/tool names, parameters, outputs, confidence, evidence.

Per the build guide Section 6: "Internal chain-of-thought is explicitly NOT
evaluated — only the execution trace is."
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Optional

# In-memory trace store (swap for DB in production)
_trace_store: dict[str, dict] = {}


def build_trace(
    query_id: str,
    query: str,
    input_summary: dict,
    task_type: Optional[str],
    tool_id: Optional[str],
    parameters: dict,
    result: Optional[dict],
    confidence: float,
    duration: float,
    error: Optional[str] = None,
) -> dict:
    """
    Build and store an execution trace.

    This matches the graded schema from Section 6:
    {
      "query": "...",
      "input_summary": {...},
      "selected_task": "...",
      "selected_tool": "...",
      "parameters_used": {...},
      "confidence": 0.87,
      "evidence": {...},
      "answer": "..."
    }
    """
    trace = {
        "query_id": query_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "query": query,
        "input_summary": input_summary,
        "selected_task": task_type,
        "selected_tool": tool_id,
        "parameters_used": parameters,
        "confidence": confidence,
        "evidence": _extract_evidence(result) if result else {},
        "answer": _extract_answer(result) if result else None,
        "processing_time_ms": round(duration * 1000, 1),
        "status": "error" if error else "success",
        "error": error,
    }

    # Store for later retrieval via /api/trace/{query_id}
    _trace_store[query_id] = trace

    return trace


def get_trace(query_id: str) -> Optional[dict]:
    """Retrieve a previously stored trace."""
    return _trace_store.get(query_id)


def get_all_traces() -> list[dict]:
    """Return all stored traces (most recent first)."""
    traces = list(_trace_store.values())
    traces.sort(key=lambda t: t.get("timestamp", ""), reverse=True)
    return traces


def _extract_evidence(result: dict) -> dict:
    """Pull out spatial/visual evidence from the result for the trace."""
    evidence = result.get("evidence", {})

    # Include change map reference if present
    if "change_map_ref" in result:
        evidence["change_map_ref"] = result["change_map_ref"]

    # Include bounding boxes summary
    if "bounding_boxes" in evidence:
        evidence["num_detections"] = len(evidence["bounding_boxes"])

    # Include class distribution for fusion
    if "class_distribution" in evidence:
        evidence["dominant_class"] = max(
            evidence["class_distribution"],
            key=evidence["class_distribution"].get,
        ) if evidence["class_distribution"] else None

    return evidence


def _extract_answer(result: dict) -> Optional[str]:
    """Pull the answer text from the result."""
    return result.get("answer") or result.get("caption")
