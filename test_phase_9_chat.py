"""
SatQuery AI — Phase 9 Test Suite: Session-Aware AI Chat

Verifies:
1. Ollama Provider registration, fallback handling, and LLM resolution chain.
2. SessionContextManager authoritative fact gathering and ground-truth compilation.
3. Cached analysis detection: 'can_answer_from_cache' rules.
4. Multi-turn session conversational memory persisted in chat_messages table.
5. Zero repeated image processing: cached queries answered from SQLite cache.
6. REST API endpoints:
   - POST /api/sessions/{session_id}/chat
   - GET /api/sessions/{session_id}/chat/history
   - GET /api/sessions/{session_id}/cache
7. Verification of zero Chain-of-Thought (CoT) leakage in public answers.
"""

from __future__ import annotations

import os
import sys
import time
import uuid
import httpx
from sqlalchemy.orm import Session

# Add project root to path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.database.session import get_db, SessionLocal
from backend.database.models import (
    SessionRecord,
    ImageRecord,
    MetadataRecord,
    AnalysisResultRecord,
    ChatMessageRecord,
)
from backend.providers.registry import ProviderRegistry
from backend.providers.ollama_provider import OllamaProvider
from backend.providers.local_llm_provider import LocalLLMProvider
from backend.providers.deepseek_provider import DeepSeekProvider
from backend.services.context_manager import SessionContextManager
from backend.services.chatbot_service import answer_session_chat
from backend.services.session_service import SessionService

BASE_URL = "http://localhost:8000"


def setup_test_session_with_cache(db: Session) -> str:
    """Helper to populate an active session with optical+SAR fusion findings."""
    session_id = f"test_p9_{uuid.uuid4().hex[:8]}"

    # 1. Create Session
    session = SessionRecord(
        id=session_id,
        title="Brahmaputra Flood Plain Monitoring",
        location_name="Assam, India",
        latitude=26.2006,
        longitude=92.9376,
    )
    db.add(session)
    db.commit()

    # 2. Add Optical Image Record
    opt_img = ImageRecord(
        id=f"img_opt_{uuid.uuid4().hex[:6]}",
        session_id=session_id,
        filename="sentinel2_optical.tif",
        file_path="/storage/sentinel2_optical.tif",
        file_size_bytes=1048576,
        format="GTiff",
    )
    db.add(opt_img)
    db.flush()

    opt_meta = MetadataRecord(
        image_id=opt_img.id,
        width=512,
        height=512,
        band_count=4,
        is_multispectral=True,
        crs="EPSG:4326",
    )
    db.add(opt_meta)

    # 3. Add SAR Image Record
    sar_img = ImageRecord(
        id=f"img_sar_{uuid.uuid4().hex[:6]}",
        session_id=session_id,
        filename="sentinel1_sar.tif",
        file_path="/storage/sentinel1_sar.tif",
        file_size_bytes=524288,
        format="GTiff",
    )
    db.add(sar_img)
    db.flush()

    sar_meta = MetadataRecord(
        image_id=sar_img.id,
        width=512,
        height=512,
        band_count=2,
        is_multispectral=False,
        crs="EPSG:4326",
    )
    db.add(sar_meta)

    # 4. Add Cached Optical + SAR Fusion Analysis Result
    fusion_evidence = {
        "fusion_mode": "deep",
        "class_distribution": {
            "water": 24.5,
            "built_up": 14.2,
            "dense_vegetation": 38.0,
            "sparse_vegetation": 15.3,
            "bare_soil": 8.0,
        },
        "water_detection": {
            "area_percentage": 24.5,
            "mean_backscatter_db": -21.8,
            "mean_mndwi": 0.58,
            "cloud_penetrated": True,
        },
        "built_up_detection": {
            "area_percentage": 14.2,
            "mean_backscatter_db": -4.2,
            "mean_ndbi": 0.35,
        },
        "vegetation_analysis": {
            "total_vegetation_percentage": 53.3,
            "dense_percentage": 38.0,
            "sparse_percentage": 15.3,
            "mean_ndvi": 0.64,
            "volume_scattering_ratio": 0.42,
        },
        "cross_modal_explanation": {
            "cloud_occlusion_percentage": 12.0,
            "sar_compensations": ["water_lake_east", "river_embankment"],
            "concordance_score": 0.94,
        },
        "overlay_url": "/api/sessions/test_p9/masks/fusion_overlay.png",
    }

    fusion_res = AnalysisResultRecord(
        id=f"res_{uuid.uuid4().hex[:8]}",
        session_id=session_id,
        query_id="query_fusion_001",
        task_type="optical_sar_fusion",
        tool_used="rs_optical_sar_fusion_v1",
        confidence=0.96,
        answer="Optical and SAR cross-modal fusion identified 24.5% open water, 14.2% built-up surface, and 53.3% total vegetation with radar cloud penetration.",
        reasoning="Dual-branch cross-attention mapped specular radar reflectance to water bodies while optical NIR resolved vegetation vigor.",
        evidence_json=fusion_evidence,
    )
    db.add(fusion_res)
    db.commit()

    return session_id


def test_ollama_provider_registration_and_fallback():
    """Verify Ollama provider lifecycle, fallback, and resolution chain."""
    registry = ProviderRegistry.get_instance()
    ollama = registry.get("ollama")

    assert ollama is not None, "OllamaProvider should be registered in ProviderRegistry"
    assert isinstance(ollama, OllamaProvider)
    assert "deepseek-r1:latest" in ollama.models
    assert "llama3:latest" in ollama.models

    # Verify fallback resolution
    # When Ollama is offline (no daemon on 11434), get_llm_provider falls back safely
    llm_p = registry.get_llm_provider("ollama")
    assert llm_p is not None
    # Must be an LLM provider instance
    assert hasattr(llm_p, "generate_chat")


def test_session_context_manager_fact_compilation():
    """Verify SessionContextManager compiles structured facts without vision reprocessing."""
    db = SessionLocal()
    try:
        session_id = setup_test_session_with_cache(db)

        facts = SessionContextManager.get_session_facts(session_id, db)
        assert facts["exists"] is True
        assert facts["title"] == "Brahmaputra Flood Plain Monitoring"
        assert len(facts["images"]) == 2
        assert facts["has_cache"] is True
        assert facts["fusion"] is not None

        # Check fusion facts details
        f = facts["fusion"]
        assert f["water_detection"]["area_percentage"] == 24.5
        assert f["water_detection"]["mean_backscatter_db"] == -21.8
        assert f["built_up_detection"]["area_percentage"] == 14.2
        assert f["cross_modal_explanation"]["cloud_occlusion_percentage"] == 12.0
        assert f["cross_modal_explanation"]["concordance_score"] == 0.94

        # Test system prompt generation
        sys_prompt = SessionContextManager.build_system_prompt(facts)
        assert "Water=24.5%" in sys_prompt
        assert "-21.8 dB" in sys_prompt
        assert "Built-Up=14.2%" in sys_prompt
        assert "Cloud Occlusion: 12.0%" in sys_prompt

    finally:
        db.close()


def test_can_answer_from_cache_decision_rules():
    """Verify rule: 'The chat must answer using cached analysis unless a new model is required.'"""
    db = SessionLocal()
    try:
        session_id = setup_test_session_with_cache(db)
        facts = SessionContextManager.get_session_facts(session_id, db)

        # 1. Questions answerable from cached analysis
        can_cache, reason = SessionContextManager.can_answer_from_cache("What is the water percentage?", facts)
        assert can_cache is True, f"Expected True for water question, got {can_cache} ({reason})"

        can_cache, reason = SessionContextManager.can_answer_from_cache("How much built up area is in this scene?", facts)
        assert can_cache is True

        can_cache, reason = SessionContextManager.can_answer_from_cache("What did the radar and optical fusion find?", facts)
        assert can_cache is True

        can_cache, reason = SessionContextManager.can_answer_from_cache("Tell me about vegetation and NDVI", facts)
        assert can_cache is True

        can_cache, reason = SessionContextManager.can_answer_from_cache("Can you summarize the findings earlier?", facts)
        assert can_cache is True

        # 2. Questions requesting uncomputed specialist model tasks
        can_cache, reason = SessionContextManager.can_answer_from_cache("Run change detection comparing these images", facts)
        assert can_cache is False, "Expected False for uncomputed change detection task"
        assert "uncomputed task" in reason.lower()

        can_cache, reason = SessionContextManager.can_answer_from_cache("Give me bounding boxes for aircraft using grounding", facts)
        assert can_cache is False, "Expected False for uncomputed grounding task"

    finally:
        db.close()


async def test_session_aware_chat_and_multi_turn_memory():
    """Verify multi-turn chat execution, cached analysis answering, and DB persistence."""
    db = SessionLocal()
    try:
        session_id = setup_test_session_with_cache(db)

        # Turn 1: Ask about water percentage
        t0 = time.perf_counter()
        resp1 = await answer_session_chat(
            session_id=session_id,
            prompt="What is the water percentage detected in this session?",
            db=db,
            preferred_provider="local_llm",
        )
        t_elapsed = (time.perf_counter() - t0) * 1000

        assert resp1["success"] is True
        assert resp1["used_cached_analysis"] is True
        assert "24.5%" in resp1["answer"] or "water" in resp1["answer"].lower()
        # Fast execution using cache (no 5+ second vision re-run)
        assert t_elapsed < 1000, f"Cached answer should be sub-second, took {t_elapsed}ms"

        # Verify chat_messages DB records
        history = SessionService.get_session_chat_history(db, session_id)
        assert len(history) == 2  # user + assistant
        assert history[0].role == "user"
        assert "water percentage" in history[0].content
        assert history[1].role == "assistant"
        assert history[1].content == resp1["answer"]

        # Turn 2: Follow-up question about built-up area
        resp2 = await answer_session_chat(
            session_id=session_id,
            prompt="And what about the built up area and buildings?",
            db=db,
            preferred_provider="local_llm",
        )
        assert resp2["success"] is True
        assert resp2["used_cached_analysis"] is True
        assert "14.2%" in resp2["answer"] or "built" in resp2["answer"].lower()

        # Verify multi-turn history length updated
        history_after = SessionService.get_session_chat_history(db, session_id)
        assert len(history_after) == 4  # 2 user turns + 2 assistant turns

        # Turn 3: Follow-up asking for summary
        resp3 = await answer_session_chat(
            session_id=session_id,
            prompt="Can you summarize the overall findings for this area?",
            db=db,
            preferred_provider="local_llm",
        )
        assert resp3["success"] is True
        assert resp3["used_cached_analysis"] is True
        assert "cached" in resp3["answer"].lower() or "summary" in resp3["answer"].lower()

    finally:
        db.close()


def test_rest_api_session_chat_endpoints():
    """Verify FastAPI endpoints for Phase 9 session chat, history, and cache."""
    db = SessionLocal()
    try:
        session_id = setup_test_session_with_cache(db)
    finally:
        db.close()

    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        # 1. Test GET /api/sessions/{session_id}/cache
        cache_resp = client.get(f"/api/sessions/{session_id}/cache")
        assert cache_resp.status_code == 200, f"Cache endpoint failed: {cache_resp.text}"
        cache_data = cache_resp.json()
        assert cache_data["exists"] is True
        assert cache_data["has_cache"] is True
        assert cache_data["fusion"] is not None

        # 2. Test POST /api/sessions/{session_id}/chat (Turn 1)
        chat_payload = {
            "message": "What is the measured water area percentage and radar backscatter?",
            "preferred_provider": "local_llm",
            "temperature": 0.5,
        }
        chat_resp = client.post(f"/api/sessions/{session_id}/chat", json=chat_payload)
        assert chat_resp.status_code == 200, f"Chat POST failed: {chat_resp.text}"
        chat_data = chat_resp.json()
        assert chat_data["success"] is True
        assert chat_data["session_id"] == session_id
        assert chat_data["used_cached_analysis"] is True
        assert len(chat_data["answer"]) > 0
        assert "<think>" not in chat_data["answer"], "No CoT leakage in public answer"

        # 3. Test POST /api/sessions/{session_id}/chat (Turn 2 Follow-up)
        followup_payload = {
            "message": "Tell me about the vegetation and canopy cover.",
            "preferred_provider": "local_llm",
        }
        followup_resp = client.post(f"/api/sessions/{session_id}/chat", json=followup_payload)
        assert followup_resp.status_code == 200
        followup_data = followup_resp.json()
        assert followup_data["success"] is True
        assert followup_data["used_cached_analysis"] is True

        # 4. Test GET /api/sessions/{session_id}/chat/history
        hist_resp = client.get(f"/api/sessions/{session_id}/chat/history")
        assert hist_resp.status_code == 200
        hist_data = hist_resp.json()
        assert hist_data["session_id"] == session_id
        assert hist_data["total_messages"] >= 4
        # Verify chronological order
        messages = hist_data["messages"]
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "user"
        assert messages[3]["role"] == "assistant"

        # 5. Test 404 for non-existent session
        non_existent = client.post("/api/sessions/fake_session_123/chat", json={"message": "hello"})
        assert non_existent.status_code == 404


if __name__ == "__main__":
    print("=" * 70)
    print("RUNNING SATQUERY AI PHASE 9 (SESSION-AWARE CHAT) TESTS")
    print("=" * 70)

    test_ollama_provider_registration_and_fallback()
    print("[PASS] test_ollama_provider_registration_and_fallback passed")

    test_session_context_manager_fact_compilation()
    print("[PASS] test_session_context_manager_fact_compilation passed")

    test_can_answer_from_cache_decision_rules()
    print("[PASS] test_can_answer_from_cache_decision_rules passed")

    import asyncio
    asyncio.run(test_session_aware_chat_and_multi_turn_memory())
    print("[PASS] test_session_aware_chat_and_multi_turn_memory passed")

    test_rest_api_session_chat_endpoints()
    print("[PASS] test_rest_api_session_chat_endpoints passed")

    print("\n" + "=" * 70)
    print("ALL PHASE 9 SESSION-AWARE CHAT TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)
