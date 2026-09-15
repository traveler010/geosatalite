"""
SatQuery AI — NVIDIA Nemotron Vision Provider

Connects to nvidia/nemotron-parse-2.0 on NVIDIA Integrate API for visual parsing,
bounding box extraction, and class detection.
"""

from __future__ import annotations

import base64
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    OpenAI = None

from backend.config import (
    NVIDIA_BASE_URL,
    NVIDIA_VISION_API_KEY,
    NVIDIA_VISION_MODEL,
)
from backend.core.logging import get_logger
from backend.providers.base import BaseVisionProvider, ProviderStatus, VisionResult

logger = get_logger("providers.nvidia")


def encode_image_to_data_url(image_path: Path | str) -> str:
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found at {path}")
    ext = path.suffix.lower()
    mime = "image/png" if ext == ".png" else "image/jpeg"
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime};base64,{b64}"


class NvidiaProvider(BaseVisionProvider):
    """NVIDIA Nemotron Parse 2.0 Visual Provider."""

    def __init__(self):
        super().__init__("nvidia_vision")
        self.model = NVIDIA_VISION_MODEL
        self.base_url = NVIDIA_BASE_URL
        self.api_key = NVIDIA_VISION_API_KEY
        self._client: Optional[OpenAI] = None

    async def initialize(self) -> bool:
        if not HAS_OPENAI:
            logger.warning("openai package missing. NvidiaProvider running in OFFLINE mode.")
            self.status = ProviderStatus.OFFLINE
            return False
        if not self.api_key:
            logger.warning("NVIDIA_VISION_API_KEY not set. NvidiaProvider running in OFFLINE mode.")
            self.status = ProviderStatus.OFFLINE
            return False
        try:
            self._client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
                timeout=20.0,
            )
            self.status = ProviderStatus.HEALTHY
            logger.info("NvidiaProvider initialized successfully.")
            return True
        except Exception as err:
            logger.warning(f"Could not initialize NVIDIA Vision client: {err}")
            self.status = ProviderStatus.OFFLINE
            return False

    async def health_check(self) -> ProviderStatus:
        if not self._client or not self.api_key:
            self.status = ProviderStatus.OFFLINE
            return self.status
        self.status = ProviderStatus.HEALTHY
        return self.status

    async def parse_visual(
        self,
        image_path_or_url: str,
        prompt: Optional[str] = None,
        task_tokens: Optional[List[str]] = None,
    ) -> VisionResult:
        t0 = time.perf_counter()
        if not self.is_available() or not self._client:
            return VisionResult(
                success=False,
                error="NvidiaProvider is offline or unconfigured.",
                model=self.model,
                latency_ms=(time.perf_counter() - t0) * 1000,
            )

        # Prepare image payload
        if image_path_or_url.startswith(("http://", "https://", "data:")):
            image_url = image_path_or_url
        else:
            try:
                image_url = encode_image_to_data_url(image_path_or_url)
            except Exception as err:
                return VisionResult(
                    success=False,
                    error=f"Failed to encode image: {err}",
                    model=self.model,
                    latency_ms=(time.perf_counter() - t0) * 1000,
                )

        tokens = task_tokens or ["<predict_bbox>", "<predict_classes>", "<output_markdown>"]
        full_prompt = f"{prompt or 'Parse this remote sensing satellite image.'}\n{' '.join(tokens)}"

        content_payload = [
            {"type": "text", "text": full_prompt},
            {"type": "image_url", "image_url": {"url": image_url}},
        ]

        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": content_payload}],
                temperature=0.1,
                max_tokens=4096,
                stream=False,
            )
            raw_text = response.choices[0].message.content or ""
            return VisionResult(
                text=raw_text,
                markdown=raw_text,
                model=self.model,
                latency_ms=(time.perf_counter() - t0) * 1000,
                success=True,
            )
        except Exception as err:
            logger.error(f"NVIDIA vision parsing failed: {err}")
            return VisionResult(
                success=False,
                error=str(err),
                model=self.model,
                latency_ms=(time.perf_counter() - t0) * 1000,
            )
