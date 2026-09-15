"""
SatQuery AI — Ollama Local LLM Provider

Connects to a local Ollama daemon (http://localhost:11434) to run models
such as llama3.2, mistral, deepseek-r1, or phi3 without internet connectivity.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
import httpx

from backend.config import OLLAMA_BASE_URL, OLLAMA_MODEL
from backend.core.logging import get_logger
from backend.providers.base import BaseLLMProvider, LLMResult, ProviderStatus

logger = get_logger("providers.ollama")


class OllamaProvider(BaseLLMProvider):
    """Ollama Local LLM Provider."""

    def __init__(
        self,
        base_url: str = OLLAMA_BASE_URL,
        model: str = OLLAMA_MODEL,
        timeout: float = 8.0,
    ):
        super().__init__("ollama")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.models = [model, "deepseek-r1:latest", "llama3:latest"]
        self.timeout = timeout
        self._available_models: List[str] = []

    def get_metadata(self):
        from backend.providers.base import ProviderMetadata
        return ProviderMetadata(
            name=self.name,
            provider_type=self.provider_type,
            status=self.status,
            version="1.0.0",
            models=self.models,
            description="Local Ollama LLM provider for zero-cloud latency and privacy",
            is_mock=False,
            details={"base_url": self.base_url, "default_model": self.model},
        )

    async def initialize(self) -> bool:
        """Probe the local Ollama daemon and fetch installed models."""
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    models = data.get("models", [])
                    self._available_models = [m.get("name", "") for m in models]
                    self.status = ProviderStatus.HEALTHY
                    logger.info(f"Ollama daemon online. Found {len(self._available_models)} model(s): {self._available_models}")
                    return True
        except Exception as e:
            logger.debug(f"Ollama local daemon not reachable ({e}). Running in OFFLINE mode.")

        self.status = ProviderStatus.OFFLINE
        return False

    async def health_check(self) -> ProviderStatus:
        """Verify Ollama connection health."""
        try:
            async with httpx.AsyncClient(timeout=1.5) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                if resp.status_code == 200:
                    self.status = ProviderStatus.HEALTHY
                    return self.status
        except Exception:
            pass

        self.status = ProviderStatus.OFFLINE
        return self.status

    async def generate_chat(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> LLMResult:
        """
        Execute multi-turn chat completion using Ollama.
        """
        t0 = time.perf_counter()

        if not self.is_available():
            # Quick health re-check in case Ollama just started
            await self.health_check()
            if not self.is_available():
                return LLMResult(
                    content="Ollama local service is offline or unreachable.",
                    success=False,
                    error="Ollama daemon unreachable on " + self.base_url,
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
            ctx_items = [f"{k}: {v}" for k, v in context.items() if v]
            if ctx_items:
                messages.append({
                    "role": "system",
                    "content": "Active Geospatial & Session Context:\n" + "\n".join(ctx_items),
                })

        # Append previous conversation history if provided
        if conversation_history:
            for turn in conversation_history:
                role = turn.get("role", "user")
                content = turn.get("content", "")
                if role in ("user", "assistant") and content:
                    messages.append({"role": role, "content": content})

        # Add current user prompt
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(f"{self.base_url}/api/chat", json=payload)
                if resp.status_code != 200:
                    return LLMResult(
                        content="",
                        success=False,
                        error=f"Ollama error {resp.status_code}: {resp.text}",
                        model=self.model,
                        latency_ms=(time.perf_counter() - t0) * 1000,
                    )

                data = resp.json()
                msg = data.get("message", {})
                content = msg.get("content", "")
                latency = (time.perf_counter() - t0) * 1000

                usage_dict = {
                    "prompt_tokens": data.get("prompt_eval_count", 0),
                    "completion_tokens": data.get("eval_count", 0),
                    "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
                }

                return LLMResult(
                    content=content,
                    reasoning=None,
                    model=self.model,
                    latency_ms=latency,
                    usage=usage_dict,
                    success=True,
                )
        except Exception as err:
            logger.error(f"Ollama chat call failed: {err}")
            return LLMResult(
                content="",
                success=False,
                error=str(err),
                model=self.model,
                latency_ms=(time.perf_counter() - t0) * 1000,
            )
