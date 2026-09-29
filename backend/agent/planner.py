"""
SatQuery AI — Agent Execution Planner

Selects specialist tools from the registry and binds only schema-permitted parameters.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.agent.model_registry import ToolSchema, get_tools_for_task
from backend.core.logging import get_logger

logger = get_logger("agent.planner")


class ExecutionPlan(BaseModel):
    task_type: str
    tool_id: str
    tool_name: str
    parameters: Dict[str, Any]
    reference_model: str
    evaluation_benchmarks: List[str]


class ExecutionPlanner:
    """Plans tool selection and parameter configuration."""

    @classmethod
    def create_plan(
        cls,
        task_type: str,
        query_text: str,
        validated_input: Dict[str, Any],
        user_params: Optional[Dict[str, Any]] = None,
    ) -> ExecutionPlan:
        """Construct a bounded, verifiable execution plan."""
        tools = get_tools_for_task(task_type)
        if not tools:
            # Fallback to general VQA
            tools = get_tools_for_task("vqa")

        selected_tool: ToolSchema = tools[0]
        schema_params = selected_tool.parameters

        # Bind only permitted parameters
        bound_params: Dict[str, Any] = {}
        user_p = user_params or {}

        # Deduce question_type for VQA
        if task_type == "vqa" and "question_type" in schema_params:
            q_lower = query_text.lower()
            if any(w in q_lower for w in ("is there", "are there", "presence", "does it have")):
                q_type = "presence"
            elif any(w in q_lower for w in ("how many", "count", "number of")):
                q_type = "count"
            elif any(w in q_lower for w in ("compare", "difference", "more", "less")):
                q_type = "comparison"
            elif any(w in q_lower for w in ("what type", "urban or", "classification")):
                q_type = "scene"
            else:
                q_type = "reasoning"
            bound_params["question_type"] = q_type

        # Bind change classes for change detection
        if task_type == "change_detection" and "change_classes" in schema_params:
            bound_params["change_classes"] = user_p.get("change_classes", "all")
            bound_params["output_format"] = "change_map"

        # Bind captioning detail level
        if task_type == "captioning" and "detail_level" in schema_params:
            bound_params["detail_level"] = user_p.get("detail_level", "detailed")

        logger.info(f"Generated execution plan: tool='{selected_tool.tool_id}' params={bound_params}")

        return ExecutionPlan(
            task_type=task_type,
            tool_id=selected_tool.tool_id,
            tool_name=selected_tool.display_name,
            parameters=bound_params,
            reference_model=selected_tool.reference_model,
            evaluation_benchmarks=selected_tool.evaluation_benchmarks,
        )
