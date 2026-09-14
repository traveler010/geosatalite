"""
SatQuery AI — Visual Image Processing Service (NVIDIA Nemotron Parse 2.0)

Performs visual parsing, object grounding bounding boxes, classes, and markdown extraction
using nvidia/nemotron-parse-2.0 on NVIDIA's Integrate API.
"""

from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from openai import OpenAI
from backend.config import (
    NVIDIA_BASE_URL,
    NVIDIA_VISION_API_KEY,
    NVIDIA_VISION_MODEL,
)

logger = logging.getLogger("satquery.vision")

_client: Optional[OpenAI] = None


def get_vision_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            base_url=NVIDIA_BASE_URL,
            api_key=NVIDIA_VISION_API_KEY,
            timeout=90.0,
        )
    return _client


def encode_image_to_data_url(image_path: Path | str) -> str:
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found at {path}")
    ext = path.suffix.lower()
    mime = "image/png" if ext == ".png" else "image/jpeg"
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime};base64,{b64}"


def parse_visual_image(
    image_input: str,
    prompt_tokens: str = "</s><s><predict_bbox><predict_classes><output_markdown><predict_text_in_pic>",
    max_tokens: int = 2048,
    temperature: float = 0.0,
    top_p: float = 1.0,
) -> Dict[str, Any]:
    """
    Parse an image using nvidia/nemotron-parse-2.0.
    image_input can be an HTTP URL, data URL, or a local file path.
    """
    client = get_vision_client()

    # Determine image URL format
    if image_input.startswith("http://") or image_input.startswith("https://") or image_input.startswith("data:"):
        image_url = image_input
    else:
        # Local file path -> encode to base64 data URI
        try:
            image_url = encode_image_to_data_url(image_input)
        except Exception as err:
            return {
                "success": False,
                "error": f"Failed to encode image: {err}",
                "content": "",
            }

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt_tokens},
                {
                    "type": "image_url",
                    "image_url": {"url": image_url},
                },
            ],
        }
    ]

    try:
        completion = client.chat.completions.create(
            model=NVIDIA_VISION_MODEL,
            messages=messages,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            stream=False,
        )

        content = completion.choices[0].message.content or ""
        finish_reason = completion.choices[0].finish_reason

        return {
            "success": True,
            "model": NVIDIA_VISION_MODEL,
            "content": content,
            "finish_reason": finish_reason,
            "usage": completion.usage.model_dump() if completion.usage else None,
        }
    except Exception as e:
        logger.error(f"Nemotron Parse visual processing failed: {e}")
        return {
            "success": False,
            "model": NVIDIA_VISION_MODEL,
            "error": str(e),
            "content": "",
        }
