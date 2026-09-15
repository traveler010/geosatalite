"""
SatQuery AI — DeepSeek Reasoning Provider (via NVIDIA Integrate API)

Connects to deepseek-ai/deepseek-v4-flash-0731 with thinking/reasoning extraction.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

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
from backend.core.logging import get_logger
from backend.providers.base import BaseLLMProvider, LLMResult, ProviderStatus

logger = get_logger("providers.deepseek")


class DeepSeekProvider(BaseLLMProvider):
    """DeepSeek LLM Provider via NVIDIA Integrate API."""

    def __init__(self):
        super().__init__("deepseek")
        self.model = NVIDIA_CHAT_MODEL
        self.base_url = NVIDIA_BASE_URL
        self.api_key = NVIDIA_CHAT_API_KEY
        self._client: Optional[OpenAI] = None

    async def initialize(self) -> bool:
        if not HAS_OPENAI:
            logger.warning("openai package missing. DeepSeekProvider running in OFFLINE mode.")
            self.status = ProviderStatus.OFFLINE
            return False
        if not self.api_key:
            logger.warning("NVIDIA_CHAT_API_KEY not configured. DeepSeekProvider running in OFFLINE mode.")
            self.status = ProviderStatus.OFFLINE
            return False
        try:
            self._client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
                timeout=12.0,
            )
            self.status = ProviderStatus.HEALTHY
            logger.info("DeepSeekProvider initialized successfully.")
            return True
        except Exception as err:
            logger.warning(f"Could not initialize DeepSeek client: {err}")
            self.status = ProviderStatus.OFFLINE
            return False

    async def health_check(self) -> ProviderStatus:
        if not self._client or not self.api_key:
            self.status = ProviderStatus.OFFLINE
            return self.status
        self.status = ProviderStatus.HEALTHY
        return self.status

    async def generate_chat(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResult:
        t0 = time.perf_counter()
        if not self.is_available() or not self._client:
            return LLMResult(
                content="DeepSeek service is offline or unconfigured.",
                success=False,
                error="Provider unavailable",
                model=self.model,
                latency_ms=(time.perf_counter() - t0) * 1000,
            )

        messages = []
        default_system = (
            "You are SatQuery AI, an expert agentic assistant for Multimodal Remote Sensing, "
            "satellite image analysis (optical, SAR, multispectral), and Earth observation intelligence."
        )
        messages.append({"role": "system", "content": system_prompt or default_system})

        if context:
            context_items = [f"{k}: {v}" for k, v in context.items() if v]
            if context_items:
                messages.append({
                    "role": "system",
                    "content": "Active Geospatial Context:\n" + "\n".join(context_items),
                })

        messages.append({"role": "user", "content": prompt})

        try:
            completion = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
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
            message = choice.message
            content = message.content or ""

            # Extract reasoning chain-of-thought
            reasoning = None
            if hasattr(message, "reasoning_content") and message.reasoning_content:
                reasoning = message.reasoning_content
            elif hasattr(message, "reasoning") and message.reasoning:
                reasoning = message.reasoning
            elif "<think>" in content and "</think>" in content:
                parts = content.split("</think>")
                reasoning = parts[0].replace("<think>", "").strip()
                content = parts[1].strip()

            usage_dict = {}
            if hasattr(completion, "usage") and completion.usage:
                usage_dict = {
                    "prompt_tokens": getattr(completion.usage, "prompt_tokens", 0),
                    "completion_tokens": getattr(completion.usage, "completion_tokens", 0),
                    "total_tokens": getattr(completion.usage, "total_tokens", 0),
                }

            return LLMResult(
                content=content,
                reasoning=reasoning,
                model=self.model,
                latency_ms=(time.perf_counter() - t0) * 1000,
                usage=usage_dict,
                success=True,
            )
        except Exception as err:
            logger.error(f"DeepSeek generation failed: {err}")
            return LLMResult(
                content="",
                success=False,
                error=str(err),
                model=self.model,
                latency_ms=(time.perf_counter() - t0) * 1000,
            )
