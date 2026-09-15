"""
SatQuery AI — Agent Executor

Executes planned specialist models, collects visual evidence, aggregates outputs,
and coordinates with the LLM provider for answer synthesis without leaking CoT into the trace.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from backend.agent.execution_trace import ExecutionTrace, ExecutionTraceBuilder
from backend.agent.planner import ExecutionPlan
from backend.core.logging import get_logger
from backend.models.captioner import RemoteSensingCaptioner
from backend.models.change_detector import BiTemporalChangeModel
from backend.models.single_image_vqa import SingleImageVQAModel
from backend.models.specialists import get_specialist
from backend.providers.registry import ProviderRegistry
from backend.services.session_service import SessionService

logger = get_logger("agent.executor")

# Singletons of specialist models
_vqa_model = SingleImageVQAModel()
_captioner = RemoteSensingCaptioner()
_change_model = BiTemporalChangeModel()


class AgentExecutor:
    """Orchestrates specialist inference and trace assembly."""

    @classmethod
    async def execute_plan(
        cls,
        plan: ExecutionPlan,
        query_text: str,
        image_paths: List[str],
        images_metadata: List[Dict[str, Any]],
        trace_builder: ExecutionTraceBuilder,
        db: Optional[Session] = None,
        session_id: Optional[str] = None,
        synthesize_with_llm: bool = True,
    ) -> Dict[str, Any]:
        t0 = time.perf_counter()
        task = plan.task_type
        tool_id = plan.tool_id

        # Step 1: Model Selection Trace
        trace_builder.add_step(
            action="ModelSelection",
            component="AgentPlanner",
            details={
                "task_type": task,
                "selected_tool": tool_id,
                "parameters": plan.parameters,
                "benchmarks": plan.evaluation_benchmarks,
            },
            duration_ms=(time.perf_counter() - t0) * 1000,
        )

        t_inf_start = time.perf_counter()
        answer = ""
        confidence = 0.85
        evidence: Dict[str, Any] = {}
        reasoning_cot = None
        overlay_url = None

        # Step 2: Specialist Inference Execution
        if task == "vqa":
            result = _vqa_model.predict(
                image_path=image_paths[0],
                question=query_text,
                question_type=plan.parameters.get("question_type", "reasoning"),
                image_metadata=images_metadata[0] if images_metadata else None,
            )
            answer = result["answer"]
            confidence = result["confidence"]
            evidence = result.get("evidence", {})

        elif task == "captioning":
            result = _captioner.generate_caption(
                image_path=image_paths[0],
                detail_level=plan.parameters.get("detail_level", "detailed"),
                image_metadata=images_metadata[0] if images_metadata else None,
            )
            answer = result["caption"]
            confidence = result["confidence"]
            evidence = {"detected_classes": result.get("detected_classes", [])}

        elif task == "change_detection" and len(image_paths) >= 2:
            # Prepare overlay path
            overlay_path = None
            if session_id:
                from backend.storage.session_storage import SessionStorageManager
                storage = SessionStorageManager(session_id)
                overlay_path = storage.get_mask_path(f"change_overlay_{trace_builder.query_id[:12]}.png")

            result = _change_model.predict(
                image1_path=image_paths[0],
                image2_path=image_paths[1],
                query=query_text,
                overlay_output_path=overlay_path,
            )
            answer = result["answer"]
            confidence = result["confidence"]
            evidence = {
                "change_percentage": result.get("change_percentage", 0.0),
                "changed_regions": result.get("changed_regions", []),
                "overlay_path": result.get("overlay_path"),
            }
            if session_id and overlay_path:
                overlay_url = f"/api/sessions/{session_id}/masks/{Path(overlay_path).name}"

        elif task == "optical_sar_fusion" and len(image_paths) >= 2:
            # Fallback to specialist wrapper
            specialist = get_specialist(tool_id)
            result = specialist.predict(image_paths=image_paths, query_text=query_text, parameters=plan.parameters)
            answer = result["answer"]
            confidence = result["confidence"]
            evidence = result.get("evidence", {})

        else:
            specialist = get_specialist(tool_id)
            result = specialist.predict(image_paths=image_paths, query_text=query_text, parameters=plan.parameters)
            answer = result["answer"]
            confidence = result["confidence"]
            evidence = result.get("evidence", {})

        inf_duration = (time.perf_counter() - t_inf_start) * 1000

        # Trace Model Inference (Observable summary ONLY, no CoT)
        trace_builder.add_step(
            action="ModelInference",
            component=plan.reference_model,
            details={
                "status": "SUCCESS",
                "output_type": "textual_and_spatial_evidence",
                "confidence_score": confidence,
            },
            duration_ms=inf_duration,
        )

        # Step 3: Optional LLM Synthesis with DeepSeek / LocalLLM
        if synthesize_with_llm:
            t_llm = time.perf_counter()
            llm_provider = ProviderRegistry.get_instance().get_llm_provider()
            sys_prompt = (
                "You are SatQuery AI, an expert agentic assistant for remote sensing satellite intelligence. "
                "Synthesize an authoritative, clear answer based on the specialist model's findings. "
                "Be technically precise regarding sensors, spatial features, and radiometric characteristics."
            )
            llm_res = await llm_provider.generate_chat(
                prompt=f"User Query: {query_text}\nSpecialist Model Findings:\n{answer}\nEvidence: {evidence}",
                system_prompt=sys_prompt,
            )
            if llm_res.success and llm_res.content:
                answer = llm_res.content
                reasoning_cot = llm_res.reasoning

            trace_builder.add_step(
                action="ResponseSynthesis",
                component=llm_provider.name,
                details={
                    "model": llm_res.model,
                    "synthesis_applied": True,
                },
                duration_ms=(time.perf_counter() - t_llm) * 1000,
            )

        # Step 4: Build finalized observable trace
        built_trace: ExecutionTrace = trace_builder.build(task_type=task, tool_used=tool_id)

        # Step 5: Relational Persistence if DB and session provided
        if db and session_id:
            try:
                SessionService.record_analysis_result(
                    db=db,
                    session_id=session_id,
                    query_id=trace_builder.query_id,
                    task_type=task,
                    tool_used=tool_id,
                    confidence=confidence,
                    answer=answer,
                    reasoning=reasoning_cot,
                    evidence_json=evidence,
                )
                for step in built_trace.steps:
                    SessionService.record_execution_log(
                        db=db,
                        session_id=session_id,
                        query_id=trace_builder.query_id,
                        step_index=step.step_index,
                        action=step.action,
                        status=step.status,
                        duration_ms=step.duration_ms,
                        details_json=step.details,
                    )
            except Exception as db_err:
                logger.warning(f"Could not persist analysis to SQLite: {db_err}")

        return {
            "answer": answer,
            "reasoning": reasoning_cot,
            "confidence": confidence,
            "task_type": task,
            "tool_used": tool_id,
            "evidence": evidence,
            "trace": built_trace.dict(),
            "overlay_url": overlay_url,
            "processing_time_ms": round((time.perf_counter() - t0) * 1000, 2),
        }
