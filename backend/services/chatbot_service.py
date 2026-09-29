"""
SatQuery AI — Chatbot AI Service (Multi-Provider Reasoning & Session-Aware Context)

Supports:
- Local Ollama LLM (e.g. deepseek-r1, llama3)
- Cloud DeepSeek reasoning via NVIDIA / OpenRouter API
- Local deterministic domain fallback LLM
- Session-aware context injection & multi-turn memory
- Zero redundant image inference via cached analysis grounding
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    OpenAI = None

from backend.config import (
    NVIDIA_BASE_URL,
    NVIDIA_CHAT_API_KEY,
    NVIDIA_CHAT_MODEL,
)
from backend.providers.registry import ProviderRegistry
from backend.services.context_manager import SessionContextManager
from backend.services.session_service import SessionService

logger = logging.getLogger("satquery.chat")

# Initialize OpenAI client for NVIDIA (legacy sync helper)
_client: Optional[OpenAI] = None


def get_chat_client() -> Optional[OpenAI]:
    global _client
    if not HAS_OPENAI:
        logger.warning("openai package not installed. Chatbot service will run in fallback mode.")
        return None
    if _client is None:
        try:
            _client = OpenAI(
                base_url=NVIDIA_BASE_URL,
                api_key=NVIDIA_CHAT_API_KEY,
                timeout=12.0,
            )
        except Exception as err:
            logger.warning(f"Could not initialize NVIDIA chat client: {err}")
            return None
    return _client


async def answer_session_chat(
    session_id: str,
    prompt: str,
    db: Session,
    preferred_provider: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> Dict[str, Any]:
    """
    Phase 9 Session-Aware Chat:
    - Extracts verified ground-truth facts from prior image analyses (VQA, caption, change, fusion).
    - Determines if query can be answered directly from cache without re-running vision models.
    - Assembles multi-turn history from chat_messages table.
    - Dispatches to requested/best LLM provider (Ollama -> DeepSeek -> LocalLLM).
    - Persists user and assistant messages for full multi-turn conversational memory.
    - Records execution audit trace.
    """
    t0 = time.perf_counter()
    query_id = f"chat_{uuid.uuid4().hex[:8]}"

    # 1. Gather session facts & cache
    facts = SessionContextManager.get_session_facts(session_id, db)
    can_cache, cache_reason = SessionContextManager.can_answer_from_cache(prompt, facts)

    # 2. Build authoritative system prompt
    system_prompt = SessionContextManager.build_system_prompt(facts)

    # 3. Retrieve multi-turn sliding window history
    history = SessionContextManager.format_conversation_history(db, session_id, max_turns=8)

    # 4. Resolve LLM provider
    registry = ProviderRegistry.get_instance()
    provider = registry.get_llm_provider(preferred=preferred_provider)

    context_dict = {
        "session_id": session_id,
        "location": facts.get("location_name") or "AOI",
        "has_cached_analysis": facts.get("has_cache", False),
    }

    # 5. Call LLM provider with grounding & conversation history
    try:
        llm_res = await provider.generate_chat(
            prompt=prompt,
            system_prompt=system_prompt,
            context=context_dict,
            temperature=temperature,
            max_tokens=max_tokens,
            conversation_history=history,
        )
    except Exception as err:
        logger.error(f"Error during LLM provider execution: {err}")
        # Fallback to local LLM provider
        local_provider = registry.get_llm_provider(preferred="local_llm")
        llm_res = await local_provider.generate_chat(
            prompt=prompt,
            system_prompt=system_prompt,
            context=context_dict,
            temperature=temperature,
            max_tokens=max_tokens,
            conversation_history=history,
        )

    duration_ms = (time.perf_counter() - t0) * 1000

    # 6. Save user turn to chat_messages table
    SessionService.record_chat_message(
        db=db,
        session_id=session_id,
        role="user",
        content=prompt,
    )

    # 7. Save assistant turn to chat_messages table
    SessionService.record_chat_message(
        db=db,
        session_id=session_id,
        role="assistant",
        content=llm_res.content,
        reasoning=llm_res.reasoning,
    )

    # 8. Record observable execution trace for auditing
    try:
        SessionService.record_execution_log(
            db=db,
            session_id=session_id,
            query_id=query_id,
            step_index=1,
            action="session_chat_reasoning",
            status="completed" if llm_res.success else "degraded",
            duration_ms=duration_ms,
            details_json={
                "provider": provider.name,
                "model": llm_res.model,
                "used_cached_analysis": can_cache,
                "cache_reason": cache_reason,
                "history_turns": len(history),
                "images_referenced": len(facts.get("images", [])),
            },
        )
    except Exception as log_err:
        logger.warning(f"Could not write chat execution log: {log_err}")

    return {
        "success": llm_res.success,
        "query_id": query_id,
        "session_id": session_id,
        "answer": llm_res.content,
        "reasoning": llm_res.reasoning,
        "model": llm_res.model,
        "provider": provider.name,
        "used_cached_analysis": can_cache,
        "cache_reason": cache_reason,
        "latency_ms": round(duration_ms, 2),
        "history_length": len(history) + 2,
    }


def generate_chat_response(
    prompt: str,
    system_prompt: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    temperature: float = 1.0,
    top_p: float = 0.95,
    max_tokens: int = 4096,
) -> Dict[str, Any]:
    """
    Synchronous / legacy chat endpoint (used by controller and routes/ai.py).
    Directly queries DeepSeek via NVIDIA Integrate API with thinking mode enabled.
    """
    client = get_chat_client()
    if not client:
        return {
            "success": False,
            "model": NVIDIA_CHAT_MODEL,
            "error": "NVIDIA Chat client unavailable",
            "answer": "DeepSeek reasoning service is currently unavailable.",
            "response": "DeepSeek reasoning service is currently unavailable.",
            "reasoning": None,
        }

    messages = []
    default_system = (
        "You are SatQuery AI, an expert agentic assistant for Multimodal Remote Sensing, "
        "satellite image analysis (optical, SAR, multispectral), and Earth observation intelligence."
    )
    messages.append({"role": "system", "content": system_prompt or default_system})

    if context:
        context_str = f"Current Session Context:\nLocation: {context.get('location')}\nImage: {context.get('image_name')}"
        messages.append({"role": "system", "content": context_str})

    messages.append({"role": "user", "content": prompt})

    try:
        completion = client.chat.completions.create(
            model=NVIDIA_CHAT_MODEL,
            messages=messages,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            extra_body={
                "chat_template_kwargs": {
                    "thinking": True,
                    "reasoning_effort": "high",
                }
            },
            stream=False,
        )

        choice = completion.choices[0]
        msg = choice.message
        reasoning = getattr(msg, "reasoning", None) or getattr(msg, "reasoning_content", None)
        content = msg.content or ""

        return {
            "success": True,
            "model": NVIDIA_CHAT_MODEL,
            "answer": content,
            "response": content,
            "reasoning": reasoning,
            "usage": completion.usage.model_dump() if completion.usage else None,
        }
    except Exception as e:
        logger.error(f"DeepSeek chat completion failed: {e}")
        return {
            "success": False,
            "model": NVIDIA_CHAT_MODEL,
            "error": str(e),
            "answer": f"Inference temporarily unavailable: {e}",
            "response": f"Inference temporarily unavailable: {e}",
            "reasoning": None,
        }
