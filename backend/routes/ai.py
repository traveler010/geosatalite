"""
SatQuery AI — AI Chat & Vision Routes

Endpoints for:
- POST /api/ai/chat: DeepSeek reasoning chatbot (deepseek-ai/deepseek-v4-flash-0731)
- POST /api/ai/vision-parse: Visual image processing (nvidia/nemotron-parse-2.0)
"""

from __future__ import annotations

from typing import Optional, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

from backend.services.chatbot_service import generate_chat_response
from backend.services.vision_service import parse_visual_image

router = APIRouter(prefix="/api/ai", tags=["ai"])


class ChatRequest(BaseModel):
    message: str
    system_prompt: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    temperature: Optional[float] = 1.0
    top_p: Optional[float] = 0.95
    max_tokens: Optional[int] = 4096


class VisionParseRequest(BaseModel):
    image_url: str
    prompt_tokens: Optional[str] = "</s><s><predict_bbox><predict_classes><output_markdown><predict_text_in_pic>"
    max_tokens: Optional[int] = 2048


@router.post("/chat")
async def chat_with_deepseek(payload: ChatRequest):
    """
    Query the DeepSeek reasoning model (deepseek-ai/deepseek-v4-flash-0731).
    Returns reasoning (chain-of-thought) and content answer.
    """
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    result = generate_chat_response(
        prompt=payload.message,
        system_prompt=payload.system_prompt,
        context=payload.context,
        temperature=payload.temperature or 1.0,
        top_p=payload.top_p or 0.95,
        max_tokens=payload.max_tokens or 4096,
    )
    return result


@router.post("/vision-parse")
async def process_image_nemotron(payload: VisionParseRequest):
    """
    Process image with NVIDIA Nemotron Parse 2.0 (nvidia/nemotron-parse-2.0).
    """
    if not payload.image_url.strip():
        raise HTTPException(status_code=400, detail="Image URL or data URI cannot be empty.")

    result = parse_visual_image(
        image_input=payload.image_url,
        prompt_tokens=payload.prompt_tokens or "</s><s><predict_bbox><predict_classes><output_markdown><predict_text_in_pic>",
        max_tokens=payload.max_tokens or 2048,
    )
    return result
