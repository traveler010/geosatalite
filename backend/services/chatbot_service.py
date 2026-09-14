"""
SatQuery AI — Chatbot AI Service (DeepSeek Reasoning via NVIDIA Integrate API)

Connects to deepseek-ai/deepseek-v4-flash-0731 on NVIDIA's API with high reasoning effort.
Extracts both reasoning chain-of-thought and final response content.
"""

from __future__ import annotations

import logging
from typing import Optional, Dict, Any

from openai import OpenAI
from backend.config import (
    NVIDIA_BASE_URL,
    NVIDIA_CHAT_API_KEY,
    NVIDIA_CHAT_MODEL,
)

logger = logging.getLogger("satquery.chat")

# Initialize OpenAI client for NVIDIA
_client: Optional[OpenAI] = None


def get_chat_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            base_url=NVIDIA_BASE_URL,
            api_key=NVIDIA_CHAT_API_KEY,
            timeout=60.0,
        )
    return _client


def generate_chat_response(
    prompt: str,
    system_prompt: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    temperature: float = 1.0,
    top_p: float = 0.95,
    max_tokens: int = 4096,
) -> Dict[str, Any]:
    """
    Generate response with thinking/reasoning using deepseek-ai/deepseek-v4-flash-0731.
    """
    client = get_chat_client()

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
