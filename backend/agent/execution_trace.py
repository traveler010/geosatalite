"""
SatQuery AI — Observable Execution Trace Builder

Builds the structured, auditable execution trace required by SIH 2026.
Strict Rule: Records only observable actions (task, tool, parameters, latency, outputs).
Does NOT expose internal chain-of-thought reasoning into the trace.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TraceStep(BaseModel):
    step_index: int
    action: str  # InputValidation, TaskClassification, ToolSelection, ModelInference, EvidenceAggregation
    component: str
    status: str = "SUCCESS"  # SUCCESS, FAILED, DEGRADED
    duration_ms: float = 0.0
    details: Dict[str, Any] = Field(default_factory=dict)


class ExecutionTrace(BaseModel):
    query_id: str
    task_type: str
    tool_used: str
    total_latency_ms: float = 0.0
    steps: List[TraceStep] = Field(default_factory=list)
    observable_summary: str = ""


class ExecutionTraceBuilder:
    """Constructs auditable traces without internal reasoning leakage."""

    def __init__(self, query_id: str):
        self.query_id = query_id
        self.steps: List[TraceStep] = []
        self._start_time = time.perf_counter()

    def add_step(
        self,
        action: str,
        component: str,
        details: Dict[str, Any],
        status: str = "SUCCESS",
        duration_ms: float = 0.0,
    ) -> None:
        """
        Record an observable action.
        Sanitizes details to ensure chain-of-thought / internal reasoning is never included.
        """
        clean_details = {k: v for k, v in details.items() if k not in ("reasoning", "chain_of_thought", "thinking")}

        step = TraceStep(
            step_index=len(self.steps) + 1,
            action=action,
            component=component,
            status=status,
            duration_ms=round(duration_ms, 2),
            details=clean_details,
        )
        self.steps.append(step)

    def build(self, task_type: str, tool_used: str) -> ExecutionTrace:
        total_time = (time.perf_counter() - self._start_time) * 1000
        summary = f"Executed task '{task_type}' using '{tool_used}' across {len(self.steps)} verified steps."

        return ExecutionTrace(
            query_id=self.query_id,
            task_type=task_type,
            tool_used=tool_used,
            total_latency_ms=round(total_time, 2),
            steps=self.steps,
            observable_summary=summary,
        )
