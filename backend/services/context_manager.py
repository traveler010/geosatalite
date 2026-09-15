"""
SatQuery AI — Session Context Manager & Analysis Cache

Aggregates session parameters, image metadata, and cached specialist analysis results
into structured ground-truth facts for LLM reasoning without repeated image processing.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from backend.core.logging import get_logger
from backend.services.session_service import SessionService

logger = get_logger("services.context_manager")


class SessionContextManager:
    """Manages session facts, cached analysis retrieval, and conversation context."""

    @classmethod
    def get_session_facts(cls, session_id: str, db: Session) -> Dict[str, Any]:
        """
        Gathers all authoritative metadata and prior specialist analysis outputs
        associated with a session into a unified ground-truth knowledge dictionary.
        """
        session = SessionService.get_session(db, session_id)
        if not session:
            return {
                "session_id": session_id,
                "exists": False,
                "images": [],
                "analyses": [],
                "summary": "Session not found.",
            }

        images = SessionService.get_session_images(db, session_id)
        analyses = SessionService.get_session_analysis_history(db, session_id)

        # 1. Format image metadata
        image_facts = []
        for img in images:
            meta = img.metadata_record
            modality = "unknown"
            if meta:
                if meta.is_multispectral or meta.band_count >= 4:
                    modality = "multispectral (optical)"
                elif meta.band_count in (1, 2):
                    modality = "SAR (radar)"
                else:
                    modality = "optical RGB"

            image_facts.append({
                "image_id": img.id,
                "filename": img.filename,
                "format": img.format,
                "modality": modality,
                "dimensions": f"{meta.width}x{meta.height}" if meta else "unknown",
                "bands": meta.band_count if meta else 3,
                "crs": meta.crs if meta else "WGS84",
                "bounds_wgs84": meta.bounds_wgs84 if meta else None,
            })

        # 2. Format cached specialist analysis outputs
        analysis_facts = []
        fusion_facts = None
        change_facts = None
        caption_facts = None
        vqa_facts = []

        for a in analyses:
            ev = a.evidence_json or {}
            fact_entry = {
                "query_id": a.query_id,
                "task_type": a.task_type,
                "tool_used": a.tool_used,
                "confidence": a.confidence,
                "answer": a.answer,
                "evidence": ev,
                "timestamp": a.created_at.isoformat() if a.created_at else None,
            }
            analysis_facts.append(fact_entry)

            if a.task_type in ("optical_sar_fusion", "fusion"):
                fusion_facts = {
                    "answer": a.answer,
                    "class_distribution": ev.get("class_distribution", {}),
                    "water_detection": ev.get("water_detection", {}),
                    "built_up_detection": ev.get("built_up_detection", {}),
                    "vegetation_analysis": ev.get("vegetation_analysis", {}),
                    "cross_modal_explanation": ev.get("cross_modal_explanation", {}),
                    "overlay_url": ev.get("overlay_url"),
                }
            elif a.task_type in ("change_detection", "change_vqa"):
                change_facts = {
                    "answer": a.answer,
                    "change_percentage": ev.get("change_percentage", 0.0),
                    "changed_regions": ev.get("changed_regions", []),
                    "overlay_url": ev.get("overlay_url"),
                }
            elif a.task_type == "captioning":
                caption_facts = a.answer
            elif a.task_type == "vqa":
                vqa_facts.append(a.answer)

        return {
            "session_id": session.id,
            "exists": True,
            "title": session.title,
            "location_name": session.location_name,
            "latitude": session.latitude,
            "longitude": session.longitude,
            "images": image_facts,
            "analyses": analysis_facts,
            "fusion": fusion_facts,
            "change": change_facts,
            "caption": caption_facts,
            "vqa": vqa_facts,
            "has_cache": len(analysis_facts) > 0,
        }

    @classmethod
    def can_answer_from_cache(cls, query: str, session_facts: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Determines if a user inquiry can be answered from cached analysis
        without running new computer vision / raster processing.

        Rule: 'The chat must answer using cached analysis unless a new model is required.'
        """
        if not session_facts.get("has_cache"):
            return False, "No cached analysis available in this session."

        q = query.strip().lower()

        # Explicit commands requesting a fresh unexecuted model task
        new_task_triggers = [
            ("change detection", session_facts.get("change") is None),
            ("bi-temporal", session_facts.get("change") is None),
            ("before and after", session_facts.get("change") is None),
            ("optical and sar fusion", session_facts.get("fusion") is None),
            ("fusion analysis", session_facts.get("fusion") is None),
            ("grounding", True if ("ground" in q or "bounding box" in q or "bbox" in q) else False),
        ]

        for trigger_text, is_uncomputed in new_task_triggers:
            if trigger_text in q and is_uncomputed:
                return False, f"User explicitly requested uncomputed task: '{trigger_text}'."

        # Follow-ups & questions about existing findings
        follow_up_tokens = [
            "water", "flood", "lake", "river", "built", "urban", "building",
            "construction", "vegetation", "forest", "crop", "canopy",
            "radar", "sar", "backscatter", "decibel", "db", "cloud",
            "percentage", "percent", "area", "how much", "how many",
            "what was", "what did you", "earlier", "again", "summarize",
            "summary", "explain", "concordance", "change", "difference",
            "location", "coordinates", "resolution", "sensor",
        ]

        if any(token in q for token in follow_up_tokens):
            return True, "Query relates to previously extracted session facts and findings."

        # Conversational questions / general queries in an active session
        conversational_starters = ["what", "how", "why", "where", "is there", "are there", "can you", "tell me"]
        if any(q.startswith(s) for s in conversational_starters) and len(session_facts.get("analyses", [])) > 0:
            return True, "Conversational follow-up in analyzed session."

        return True, "Defaulting to cached conversational reasoning."

    @classmethod
    def build_system_prompt(cls, session_facts: Dict[str, Any]) -> str:
        """
        Constructs an authoritative LLM system prompt grounding the model in
        the verified remote sensing findings of the current session.
        """
        lines = [
            "You are SatQuery AI, an expert agentic assistant for Multimodal Remote Sensing and Earth Observation.",
            "You have active session memory. Use the following verified ground-truth facts extracted from the satellite imagery to answer user questions.",
            "CRITICAL RULES:",
            "1. Ground your answers strictly in the cached analysis facts below. Do NOT contradict or hallucinate new percentages or backscatter numbers.",
            "2. For follow-up questions, reference previous findings naturally.",
            "3. If asked about water, built-up areas, or vegetation, cite the exact percentages and radiometric backscatter (dB) / spectral indices (NDVI/MNDWI) measured by the specialist models.",
            "",
            f"SESSION CONTEXT:",
            f"- Title: {session_facts.get('title', 'Active Session')}",
            f"- Location: {session_facts.get('location_name') or 'AOI'} (Lat: {session_facts.get('latitude')}, Lon: {session_facts.get('longitude')})",
            f"- Uploaded Images: {len(session_facts.get('images', []))}",
        ]

        for idx, img in enumerate(session_facts.get("images", []), start=1):
            lines.append(f"  Image {idx}: {img['filename']} ({img['modality']}, {img['dimensions']}, {img['bands']} bands, CRS: {img['crs']})")

        lines.append("\nCACHED ANALYSIS FINDINGS:")

        if session_facts.get("fusion"):
            f = session_facts["fusion"]
            dist = f.get("class_distribution", {})
            w_ev = f.get("water_detection", {})
            b_ev = f.get("built_up_detection", {})
            v_ev = f.get("vegetation_analysis", {})
            xai = f.get("cross_modal_explanation", {})

            lines.extend([
                "• Optical + SAR Multimodal Fusion (Model: OpticalSARFusionNet):",
                f"  - Land Cover Distribution: Water={dist.get('water', 0)}%, Built-Up={dist.get('built_up', 0)}%, Dense Veg={dist.get('dense_vegetation', 0)}%, Sparse Veg={dist.get('sparse_vegetation', 0)}%, Bare Soil={dist.get('bare_soil', 0)}%",
                f"  - Water Analysis: {w_ev.get('area_percentage', 0)}% of AOI, Mean SAR specular backscatter: {w_ev.get('mean_backscatter_db')} dB, Mean optical MNDWI: {w_ev.get('mean_mndwi')}, Cloud penetrated: {w_ev.get('cloud_penetrated')}",
                f"  - Built-Up Analysis: {b_ev.get('area_percentage', 0)}% of AOI, Mean SAR double-bounce backscatter: {b_ev.get('mean_backscatter_db')} dB, Mean NDBI: {b_ev.get('mean_ndbi')}",
                f"  - Vegetation Analysis: Total={v_ev.get('total_vegetation_percentage', 0)}% (Dense={v_ev.get('dense_percentage', 0)}%, Sparse={v_ev.get('sparse_percentage', 0)}%), Mean NDVI={v_ev.get('mean_ndvi')}, Volume scattering ratio={v_ev.get('volume_scattering_ratio')}",
                f"  - Cloud Occlusion: {xai.get('cloud_occlusion_percentage', 0.0)}%",
                f"  - Concordance Score: {xai.get('concordance_score', 0.90)}",
            ])

        if session_facts.get("change"):
            c = session_facts["change"]
            lines.extend([
                f"• Bi-Temporal Change Detection:",
                f"  - Altered Surface: {c.get('change_percentage', 0.0)}%",
                f"  - Changed Regions: {len(c.get('changed_regions', []))}",
                f"  - Summary: {c.get('answer')}",
            ])

        if session_facts.get("caption"):
            lines.append(f"• Scene Caption: {session_facts['caption']}")

        for v in session_facts.get("vqa", []):
            lines.append(f"• Prior VQA Insight: {v}")

        return "\n".join(lines)

    @classmethod
    def format_conversation_history(
        cls,
        db: Session,
        session_id: str,
        max_turns: int = 10,
    ) -> List[Dict[str, str]]:
        """
        Fetches chronological multi-turn history from chat_messages table and formats
        into sliding-window message pairs.
        """
        records = SessionService.get_session_chat_history(db, session_id, limit=max_turns * 2)
        formatted = []
        for r in records:
            if r.role in ("user", "assistant") and r.content:
                formatted.append({
                    "role": r.role,
                    "content": r.content,
                })
        return formatted[-max_turns * 2:]
